---
applyTo: "tests/**"
---

- Test factories (`*_factory` fixtures) take every constructor argument as an optional keyword argument, so a test
  can override any default. Create a valid default only when the argument is not given.
