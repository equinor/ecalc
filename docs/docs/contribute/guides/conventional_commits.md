# Conventional Commits
Git commits are required to follow [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/).

The message should be structured like this:
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

The type can be one of these types: **feat**, **fix**, **build**, **ci**, **docs**, **style**, **refactor**, **test**, and **chore**.

The description should be lower-case for the first letter. For description of optional parts, please refer to the
[conventional Commits Docs](https://www.conventionalcommits.org/en/v1.0.0/).

Here are some simple example conventional commits:

```
feat: implement new awesome feature
```

```
docs: add developer guidelines
```

A more advanced example:
```
fix: prevent racing of requests

Introduce a request id and a reference to latest request. Dismiss
incoming responses other than from latest request.

Remove timeouts which were used to mitigate the racing issue but are
obsolete now.

Reviewed-by: Z
Refs: #123
```