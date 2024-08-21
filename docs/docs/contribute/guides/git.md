# Git

[Git](https://git-scm.com/) is the version control system (VCS) that is responsible for tracking all changes done to the code base.
Git is a distributed version control system that tracks changes in any set of computer files, and allows for collaborative development
of source code and documentation. We use Git as a service through GitHub. See [GitHub Docs](https://docs.github.com/en/get-started)
for more information about GitHub and how to get started.

:::info
If you do not want to work with files locally, GitHub lets you complete many Git-related actions directly in the browser, including:

* [Creating a repository](https://docs.github.com/en/get-started/quickstart/set-up-git#:~:text=the%20browser%2C%20including%3A-,Creating%20a%20repository,-Forking%20a%20repository)
* [Forking a repository](https://docs.github.com/en/get-started/quickstart/set-up-git#:~:text=Creating%20a%20repository-,Forking%20a%20repository,-Managing%20files)
* [Managing files](https://docs.github.com/en/get-started/quickstart/set-up-git#:~:text=Forking%20a%20repository-,Managing%20files,-Being%20social)
:::

## Setting up Git
Go to [git-scm.com](https://git-scm.com/downloads) to download the appropriate git client unless it is already installed on your system.

To verify that git is installed, you can run:
```shell
git --version
```

See [GitHub Docs - Set up Git](https://docs.github.com/en/get-started/quickstart/set-up-git) for detailed instructions.

## Using Git
Git is a powerful tool that can be used in many ways. We recommend the following resources:

1. Introduction to git - [GitHub - About git](https://docs.github.com/en/get-started/using-git/about-git)
2. How to get out of git trouble [Oh shit, Git!?!](https://ohshitgit.com/)

Below we will describe the most commonly used commands and scenarios when working with git.

:::info
In the following sections we use the syntax &ltsome text> where you should fill in your own values, such as:
* **&ltchange type>**: [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/) change types such as feat, fix, docs, test, chore, refactor, etc.
* **&ltissue number>**: the GitHub [Issue Number](https://github.com/equinor/ecalc) that you are solving. This may be omitted if you are fixing something tiny.
* **&ltdescription>**: a short summary of the code changes, e.g., fix: array parsing issue when multiple spaces were contained in string.
:::

### Cloning a git repository
Navigate to the location where you want to store the code, and clone the repository:

```shell
git clone git@github.com:equinor/ecalc.git
```

This will create a local copy of a project that already exists remotely. The copy will be stored in a sub-folder, with the
same name as the repository, ecalc/.

### Tell Git who you are
```shell
git config --global user.name "My name"
git config --global user.email example@email.com
```
This is what will show in the git log when you make changes.

### Create your own branch
In order to create a new local branch and switch to it:
```shell
git checkout -b <type of change>/<issue number>-<description>
```
for new versions of git you may also use the more intuitive.
```shell
git switch -c <type of change>/<issue number>-<description>
```

### Switch between existing branches
```shell
git checkout <branch name>
```

### Fetch changes from GitHub
```shell
git pull
```
This will update the local branch you are currently in, with changes done in GitHub.
```shell
git push --set-upstream origin <change type>/<issue number>-<description>
```

### Send your changes to GitHub
```shell
git push
```
This will update the remove repository on GitHub. If it is the first time for a new branch you will also
have to tell git that you are creating a new remote branch by using the command:

### Check status of changes
List the files you have changed and those you still need to add or commit:
```shell
git status
```

### Add files
Add new or changed files
```shell
git add <filename>
```
or adding everything in and below your working directory
```shell
git add .
```

### Commit changes
Commit any files you've added with git add, and also commit any files you've changed since then:
```shell
git commit -m "<change type>: <description"
```
This will save a snapshot to the project history and completes the change-tracking process.
Anything that has been previously staged with git add will become a part of the snapshot with git commit.

### Send changes to GitHub
In order to send changes back to GitHub, you will use the following command:
```shell
git commit -m "<change type>: <description"
```

## Workflow examples

### Pull Requests
For Equinor internal developers you are welcome to open a Pull Request directly in the [ecalc](https://github.com/equinor/ecalc/) repository.

Here's a quick guide:

1. Clone the project to your machine:
    ```shell
    git clone git@github.com:equinor/ecalc.git
    ```
2. Create a branch locally with a succinct but descriptive name and prefixed with change type.
    ```shell
    git checkout -b <change type>/<issue number>-<description of change>
    ```
3. Add the changed files
    ```shell
    git add <path to changed file(s)>
    ```
4. Commit your changes using the [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/) formatting for the commit messages.
    ```shell
    git commit -m "<change type>: <description>"
    ```
5. If your changes are in conflict with changes done by other, then you need to rebase and solve the change conflicts. This also ensures your code is running on the latest available code.
    ```shell
    git fetch
    git rebase origin/main
    ```
6. Push changes to GitHub
    ```shell
    git push --set-upstream origin <change type>/<issue number>-<description>
    ```
7. You can now [Create a Pull Request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request) 

### Fork the repository

For external developers, you will [contribute to the project through forking](https://docs.github.com/en/get-started/quickstart/contributing-to-projects).

Here's a quick guide:

1. Create your own fork of the repository
2. Clone the project to your machine
    ```shell
    git clone git@github.com:equinor/ecalc.git
    ```
3. To keep track of the original repository add another remote named upstream
    ```shell
    git remote add upstream git@github.com:equinor/template-fastapi-react.git
    ```
4. Create a branch locally with a succinct but descriptive name and prefixed with change type.
    ```shell
    git checkout -b <change type>/<issue number>-<description>
    ```
5. Make the changes in the created branch.
6. Add and run tests for your changes if needed (we only take pull requests with passing tests).
7. Add the changed files
    ```shell
    git add <path to changed file(s)>
    ```
8. Commit your changes using the [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/) formatting for the commit messages.
    ```shell
    git commit -m "<change type>: <description>"
    ```
9. Before you send the pull request, be sure to rebase onto the upstream source. This ensures your code is running on the latest available code.
    ```shell
    git fetch upstream
    git rebase upstream/main
    ```
10. Push to your fork.
    ```shell
    git push origin feature/my-new-feature
    ```
11. Submit a [Pull Request from a fork](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests creating-a-pull-request-from-a-fork). Please provide us with some explanation of why you made the changes you made. For new features make sure to explain a standard use case to us.

That's it... thank you for your contribution!

After your pull request is merged, you can safely delete your branch.
