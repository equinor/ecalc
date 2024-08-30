# Get Started

Welcome! We are glad that you want to contribute to our project! 💖

This project accepts contributions via GitHub Pull Requests.

This document outlines the process to help get your contribution accepted.

There are many ways to contribute:

* Suggest [features](https://github.com/equinor/ecalc/issues/new?assignees=&labels=&template=feature_request.md&title=)
* Suggest [changes](https://github.com/equinor/ecalc/issues/new?assignees=&labels=bug&template=code-maintainer.md&title=)
* Report [bugs](https://github.com/equinor/ecalc/issues/new?assignees=&labels=bug&template=bug_report.md&title=)

You can start by looking through the [GitHub Issues](https://github.com/equinor/ecalc/issues) filtered by labels.

:::info
We follow some contributor guidelines that you will find in our [contributor guidelines](#guidelines).

Don't worry if your contribution does not follow all the guidelines. We will guide you in the [code review process](#get-code-review).
The threshold for contributing is low, and we appreciate any contribution great or small. 🙏
:::

## Prerequisites
* See [Documentation guide](documentation-guide/documentation.md) for how to get started with contributions to this 
  documentation.

## How to contribute

Contribution is done in 3 simple steps:

### Initiate change

For major changes, please open an issue first to discuss what you would like to change. For smaller changes, it is sufficient
to explain the change without referring to an issue.

### Make a Pull Request
To contribute to the project, you will have to make the change and create a Pull Request on GitHub. How you do this depends on your role.

1. Equinor internal contributors, you may open a [Pull Request directly](guides/git.md#pull-requests),
2. Independent contributors, you will [Fork the repository](guides/git.md#fork-the-repository).

### Get code review {#get-code-review}
Once a Pull Request has been made, we will give you feedback and maybe suggest changes.

The core team looks at pull requests on a regular basis, we review the code and guide you if needed.
Here you will find more information about the
[GitHub Code Review Process](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/about-pull-request-reviews)

## Guidelines

* For major changes, please open an issue first to discuss what you would like to change
* Work on your own fork of the main repo
* Use a separate branch for each issue you’re working on
* Use conventional commit. See our [Git commit format](#git-commit-format) for details,
  and our [Git guide](guides/git.md) for our full guide
* Please include [unit tests](https://en.wikipedia.org/wiki/Unit_testing) with all your code changes
* We follow [Trunk Based Development](https://trunkbaseddevelopment.com/) style of working with short-lived feature
  branches.

## Pull Requests

Please try to make your [Pull Requests](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests) easy to review for us.

* Make small pull requests. The smaller, the faster to review and the more likely it will be merged soon.
* Don't make changes unrelated to the goals of your PR. 

While you're writing up the pull request, you can add `closes #<issue number>` in the message body where issue number
is the issue you're fixing. Therefore, an example would be `closes #42` would close issue #42.

## Git commit format
Git commits are required to follow [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/). Please see
our [Conventional Commit Guide](guides/conventional_commits.md) for examples.

## Readability
We use the [pre-commit hooks](https://pre-commit.com/) in order to ensure uniform formatting and to exclude potential code issues.

We strive for readable code. A few good tips are:

1. [Self-documenting code](https://en.wikipedia.org/wiki/Self-documenting_code) with self-explaining variable names
2. [Composition over inheritance](https://en.wikipedia.org/wiki/Composition_over_inheritance)
3. [Functional code](https://en.wikipedia.org/wiki/Functional_programming) over Object-Oriented Code
4. [Rugged code](https://ruggedsoftware.org/) to write more robust code
5. [Domain Driven Design](https://en.wikipedia.org/wiki/Domain-driven_design) to to match the code with the domain we are working on

### Code style
Except for the pre-commits hooks mentioned above, we also strive to follow the following code style:

* Use capital letters for constants i.e. SECONDS_PER_HOUR
* Try to split methods/modules/classes into smaller bits of code
* Remove, do not comment out, unused code
* Use types and type hinting
* We comment the code when it is not self-explanatory
* Be consistent with existing code style - try to make it look like the code is written by **one** developer
* For Python, we follow [PEP 8 – Style Guide for Python Code](https://peps.python.org/pep-0008/) and [PEP 20 - The Zen of Python](https://peps.python.org/pep-0020/):

```
Beautiful is better than ugly.
Explicit is better than implicit.
Simple is better than complex.
Complex is better than complicated.
Flat is better than nested.
Sparse is better than dense.
Readability counts.
Special cases aren't special enough to break the rules.
Although practicality beats purity.
Errors should never pass silently.
Unless explicitly silenced.
In the face of ambiguity, refuse the temptation to guess.
There should be one-- and preferably only one --obvious way to do it.
Although that way may not be obvious at first unless you're Dutch.
Now is better than never.
Although never is often better than *right* now.
If the implementation is hard to explain, it's a bad idea.
If the implementation is easy to explain, it may be a good idea.
Namespaces are one honking great idea -- let's do more of those!
```

Please reach out to us if you have any questions. 👋

Thank you for your contribution! 🎉