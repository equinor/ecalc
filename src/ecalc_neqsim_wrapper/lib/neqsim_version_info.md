Current neqsim.jar from latest release of NeqSim (v3.0.5 - https://github.com/equinor/neqsim/releases/tag/v3.0.5)

NeqSim is currently not considered to be thread-safe. That means that two threads working towards the same gateway, interchangely changing a fluid setting will interfere with each other.

If you need to manually compile a version, do the following:

Compile steps:

- git clone https://github.com/equinor/neqsim
- git checkout <hash>
- modify pom.xml with updated versions (if necessary)
- Compile by running `mvn -B package --file pom.xml` (See `.github/workflows/build.yml in [equinor/neqsim](https://github.com/equinor/neqsim))

Environment info:

```
$ mvn --version
Apache Maven 3.6.3
Maven home: /usr/share/maven
Java version: 1.8.0_292, vendor: Private Build, runtime: /usr/lib/jvm/java-8-openjdk-amd64/jre
Default locale: en_US, platform encoding: UTF-8
OS name: "linux", version: "5.10.0-1052-oem", arch: "amd64", family: "unix"
```

```
$ java -version
openjdk version "1.8.0_292"
OpenJDK Runtime Environment (build 1.8.0_292-8u292-b10-0ubuntu1~20.04-b10)
OpenJDK 64-Bit Server VM (build 25.292-b10, mixed mode)
```
