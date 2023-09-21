# eCalc NeqSim Wrapper

[NeqSim](https://equinor.github.io/neqsimhome/) is an open source process simulation software. NeqSim has been developed
in Java, therefore we need to have a special way to use the NeqSim Java library in eCalc. This is handled in this
package, using *py4j*.

In eCalc, we solely use NeqSim for calculation of Equation of State (EoS) for fluids, and plan to support other libraries
and methods for this in the future. The NeqSim Wrapper implementation is therefore added here as an "external" package,
to easily add it as an optional dependency in the future.
