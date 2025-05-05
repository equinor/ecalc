import enum
import uuid
import zipfile
from abc import abstractmethod
from collections import Counter
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryFile
from typing import IO, Protocol

from libecalc.common.errors.exceptions import EcalcError, EcalcErrorType
from libecalc.common.logger import logger

YAML_EXTENSIONS = [".yml", ".yaml"]
CSV_EXTENSION = ".csv"
ZIP_EXTENSION = ".zip"
MAIN_PROVEN_FILE = ["INSTALLATION", "TIME_SERIES", "FACILITY_INPUTS", "FUEL_TYPES"]

IGNORED_ZIP_CONTENTS_KEYWORDS = [".DS_Store", "__MACOSX"]


def is_main_yaml_file(file: IO) -> bool:
    """Deprecated. To be removed when zip is verified.
    :param file:
    :return:
    """
    bytes_str = file.read()
    file.seek(0)
    text_obj = bytes_str.decode("UTF-8")
    return any(x in text_obj for x in MAIN_PROVEN_FILE)


def is_ignored_zip_content(file: Path) -> bool:
    return bool(file.is_dir() or any(substring in str(file) for substring in IGNORED_ZIP_CONTENTS_KEYWORDS))


class FileWithName(Protocol):
    filename: str
    file: IO


@dataclass
class UnzippedFile:
    """Class for mimicking FileWithName."""

    filename: str  # including path
    file: IO


class EcalcFileType(str, enum.Enum):
    YAML = "yaml"
    CSV = "csv"
    ZIP = "zip"


@dataclass
class EcalcFile:
    @abstractmethod
    def is_valid(self) -> bool:
        pass

    @staticmethod
    def is_csv(filename: Path) -> bool:
        return filename.suffix.lower() == CSV_EXTENSION

    @staticmethod
    def is_yaml(filename: Path) -> bool:
        try:
            file_extension = filename.suffix
            return file_extension.lower() in YAML_EXTENSIONS
        except AttributeError as e:
            logger.exception(e)
            return False

    @staticmethod
    def is_zip(filename: Path) -> bool:
        try:
            file_extension = filename.suffix
            return file_extension.lower() in ZIP_EXTENSION
        except AttributeError as e:
            logger.exception(e)
            return False

    @staticmethod
    def get_type(filename: Path) -> EcalcFileType:
        if EcalcFile.is_csv(filename):
            return EcalcFileType.CSV
        elif EcalcFile.is_yaml(filename):
            return EcalcFileType.YAML
        elif EcalcFile.is_zip(filename):
            return EcalcFileType.ZIP

        message = f"Cannot get (valid) file type of {filename}"
        logger.warning(message)
        raise EcalcError(
            message=message,
            title="Invalid file type",
            error_type=EcalcErrorType.CLIENT_ERROR,
        )


@dataclass
class ValidEcalcFile(EcalcFile):
    """Class for mimicking FileWithName."""

    original_filename: Path  # full path, e.g. in archive
    filename: str  # just the (file)name
    file: IO
    file_type: EcalcFileType

    def is_valid(self) -> bool:
        return True

    def is_main_yaml_file(self) -> bool:
        bytes_str = self.file.read()
        self.file.seek(0)
        text_obj = bytes_str.decode("UTF-8")
        return any(x in text_obj for x in MAIN_PROVEN_FILE)


@dataclass
class InvalidEcalcFile(EcalcFile):
    """Class for mimicking FileWithName."""

    original_filename: Path  # full path in archive
    filename: str  # just the filename
    error: str

    def is_valid(self) -> bool:
        return False


@dataclass
class EcalcFiles:
    ALLOWED_EXTENSIONS = {"yaml", "csv", "yml", "zip"}

    @staticmethod
    def allowed_file(filename: str) -> bool:
        return "." in filename and Path(filename).suffix.split(".")[1] in EcalcFiles.ALLOWED_EXTENSIONS

    @staticmethod
    def get_main_file(files: list[ValidEcalcFile]) -> ValidEcalcFile:
        """Get the main yaml file. Detected by checking for a specific format. Only the main
        yaml file can have !include and a certain set of sections.

        * Only one main file is allowed

        if none or more than one main file is detected an exception is raised
        :param files:
        :return:
        """
        main_files = [file for file in files if file.is_yaml(file.original_filename) and file.is_main_yaml_file()]
        if len(main_files) > 1:
            raise EcalcError(
                "Bad Request",
                f"Only one main file is supported, the following files were detected as main files: {', '.join([main_file.filename for main_file in main_files])}",
                error_type=EcalcErrorType.CLIENT_ERROR,
            )

        if len(main_files) == 0:
            raise EcalcError(
                "Bad Request",
                "No main files found. There must be one main file",
                error_type=EcalcErrorType.CLIENT_ERROR,
            )

        return main_files[0]

    @staticmethod
    def validate_filetypes(files: list[FileWithName]) -> tuple[list[ValidEcalcFile], list[InvalidEcalcFile]]:
        """Given a list of files (e.g uploaded by a user), given a name, do an initial attempt to
        filter out bad files for further processing of good files only.

        The current validation implementation is very naĩve, by only checking file extension.

        :param files:
        :return:
        """
        valid_files: list[ValidEcalcFile] = []
        invalid_files: list[InvalidEcalcFile] = []
        for file in files:
            if EcalcFiles.allowed_file(file.filename):
                if EcalcFile.is_zip(Path(file.filename)):
                    if len(files) > 1:
                        raise EcalcError(
                            title="Invalid file combination",
                            message="A zip file cannot be combined with other file types. Please provide a zip file alone.",
                        )

                    valid_files, invalid_files = unpack_zip(file.file)
                elif EcalcFile.is_csv(Path(file.filename)) or EcalcFile.is_yaml(Path(file.filename)):
                    valid_files.append(
                        ValidEcalcFile(
                            original_filename=Path(file.filename),
                            filename=file.filename,
                            file=file.file,
                            file_type=EcalcFile.get_type(filename=Path(file.filename)),
                        )
                    )
                else:
                    invalid_files.append(
                        InvalidEcalcFile(
                            original_filename=Path(file.filename),
                            filename=file.filename,
                            error="Invalid File Extension",
                        )
                    )
            else:
                invalid_files.append(
                    InvalidEcalcFile(
                        original_filename=Path(file.filename),
                        filename=file.filename,
                        error="Invalid File Extension",
                    )
                )

        return valid_files, invalid_files


def find_longest_common_path(file_path_1: Path, file_path_2: Path) -> str:
    """Given 2 paths, find the longest common path, part by part that the 2 paths share; ie
    until which position in the file hierarchy do they diverge?

    :param file_path_1:
    :param file_path_2:
    :return:
    """
    common_path = ""
    for path_1, path_2 in zip(file_path_1.parts, file_path_2.parts):
        if path_1 == path_2:
            common_path += path_1 + "/"
        else:
            break

    return common_path


def strip_common_path(common_path: str, path: str) -> str:
    """Remove/strip the given subpath from path
    :param common_path:
    :param path:
    :return:
    """
    return path.replace(common_path, "")


def make_relative_path(linked_file: str, main_file: str) -> str:
    """Given a main file and a file to be linked to from that file, only
    include the parts of the path of both files that _differ_.

    The parts that is different in main_file, will be replaced with "../",

    :param linked_file:
    :param main_file:
    :return:
    """
    main_file_path = Path(main_file)
    for part in main_file_path.parts[:-1]:
        if part != "" and part != "/":
            linked_file = "../" + linked_file

    return linked_file


def find_duplicates(files: list[ValidEcalcFile]) -> list[str]:
    """Find files with duplicate names (names = without path).

    :param files:
    :return:
    """
    count_filenames = Counter([file.filename for file in files])
    duplicates = [filename for filename, count in count_filenames.items() if count > 1]

    return duplicates


def rename_duplicates(valid_files: list[ValidEcalcFile], duplicates: list[str]) -> dict[Path, str]:
    """Rename duplicate files. All with same name will be renamed. Those that are not duplicates,
    will also be returned, with the original filename in the mapping.

    Only resource files (csv) needs to be renamed, because they are flattened out and will then exist
    at the same level.

    :param valid_files:
    :param duplicates:
    :return:
    """
    renamed_files: dict[Path, str] = {}
    for file in valid_files:
        if file.filename in duplicates:
            renamed_filename = str(file.original_filename).replace("/", "_")
            if len(renamed_filename) > 100:
                renamed_filename = renamed_filename[-94:] + str(uuid.uuid4().hex.upper()[0:6])
            renamed_files[file.original_filename] = renamed_filename
        else:
            renamed_files[file.original_filename] = file.filename

    return renamed_files


def make_relative_paths(files: list[ValidEcalcFile], main_yaml: ValidEcalcFile) -> dict[Path, str]:
    """For all files in the list, generate the relative paths for all files, relative
    to the provided main file. All files provided, must have the original_filename set, which must
    be the relative path to the root of the model; e.g. the (zip) archive path, or
    if only one level, the filename itself.

    :param files:
    :param main_yaml:
    :return:
    """
    relative_paths: dict[Path, str] = {}
    for file in files:
        if file == main_yaml:
            # since all files are relative to this given file, this must be the filename itself, only
            relative_paths[main_yaml.original_filename] = main_yaml.filename
        else:
            common_path = find_longest_common_path(Path(file.original_filename), Path(main_yaml.original_filename))
            stripped_file = strip_common_path(common_path, str(file.original_filename))
            stripped_main = strip_common_path(common_path, str(main_yaml.original_filename))
            relative_path = make_relative_path(stripped_file, stripped_main)

            relative_paths[file.original_filename] = relative_path

    return relative_paths


def unpack_zip(file: IO) -> tuple[list[ValidEcalcFile], list[InvalidEcalcFile]]:
    """Unpack the zip similarility to how single files are handled, by returning a tuple
    of valid and invalid files.

    :param file:
    :return:
    """
    valid_files: list[ValidEcalcFile] = []
    invalid_files: list[InvalidEcalcFile] = []
    try:
        with zipfile.ZipFile(BytesIO(file.read())) as archive:
            for zip_info in archive.infolist():
                try:
                    file_path = Path(zip_info.filename)

                    if is_ignored_zip_content(file_path) or zip_info.is_dir():
                        # Just ignore, dont event mention it. Will just confuse users (because those files are normally hidden)
                        continue
                    elif EcalcFile.is_csv(file_path) or EcalcFile.is_yaml(file_path):
                        with archive.open(zip_info) as file:
                            file_like = TemporaryFile()
                            file_like.write(file.read())
                            file_like.seek(0)
                            valid_files.append(
                                ValidEcalcFile(
                                    original_filename=file_path,
                                    filename=file_path.name,
                                    file=file_like,
                                    file_type=EcalcFile.get_type(filename=file_path),
                                )
                            )
                    else:
                        invalid_files.append(
                            InvalidEcalcFile(
                                original_filename=file_path, filename=file_path.name, error="Invalid file extension"
                            )
                        )
                        continue

                except EcalcError as ee:
                    logger.warning(f"An error occurred while reading file({file_path}) in zip archive")
                    invalid_files.append(
                        InvalidEcalcFile(original_filename=file_path, filename=file_path.name, error=ee.message)
                    )

        valid_file_paths = [valid_file.original_filename for valid_file in valid_files]
        if len(valid_file_paths) != len(set(valid_file_paths)):
            raise EcalcError(title="Bad zip file", message="Duplicated filepaths in zip archive detected. Please fix.")

        return valid_files, invalid_files

    except zipfile.BadZipFile as e:
        raise EcalcError(title="Bad zip file", message="An error occurred while unpacking the zip file") from e
