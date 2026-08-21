# Python Project Coding Standards

## 1. General Principles

Code should prioritise, in order:

1. Correctness
2. Readability
3. Maintainability
4. Testability
5. Performance, where performance is materially important

Prefer straightforward, explicit code over clever or unnecessarily compact implementations.

Code should generally follow **PEP 8** unless a project-specific convention documented here takes precedence.

---

## 2. Naming

Use descriptive names that indicate the purpose of a variable, function, class, or module.

- Functions and methods: `snake_case`
- Variables: `snake_case`
- Modules: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Internal/private implementation details: prefix with `_`

Avoid unexplained abbreviations.

Prefer:

```python
chamber_spacing
shell_radius
calculate_growth_rate()
```

rather than:

```python
cs
r
calc_gr()
```

Short names such as `i`, `j`, `x`, `y`, and `z` are acceptable where their meaning is conventional and their scope is small.

---

## 3. Functions and Methods

Functions and methods should have a single clear responsibility.

Where practical:

- Keep functions reasonably short.
- Break complex operations into smaller named functions.
- Avoid excessive nesting.
- Prefer early returns where they simplify control flow.
- Avoid functions with large numbers of parameters; consider configuration objects or dataclasses where appropriate.

Functions should not unexpectedly modify their input arguments unless mutation is clearly part of their documented behaviour.

---

## 4. Docstrings

All functions and methods should have docstrings.

Docstrings should describe:

- What the function does.
- Important assumptions or behaviour.
- Parameters.
- Return value.
- Exceptions where these form part of the expected interface.

Use the following format:

```python
def calculate_radius(theta: float, growth_rate: float) -> float:
    """
    Calculate the shell radius at a specified growth angle.

    :param theta: Growth angle in radians.
    :param growth_rate: Exponential growth coefficient.
    :return: Calculated shell radius.
    """
```

`:param` and `:return:` should be included where appropriate.

Use `:raises:` where callers are reasonably expected to handle a particular exception.

---

## 5. Type Hints

Functions and methods should use Python type hints for parameters and return values.

For example:

```python
def build_aperture(radius: float, points: int) -> list[tuple[float, float]]:
```

Use precise types where practical, but avoid overly complicated type declarations that make code harder to understand.

Use `None` explicitly where appropriate:

```python
def find_shell(name: str) -> Shell | None:
```

---

## 6. Comments

Comments should explain **why** code behaves as it does rather than merely restating the code.

Complex or non-obvious sections of a method should contain explanatory `#` comments.

For example:

```python
# Offset the phase by pi/2 so the aperture starts on the positive Y axis.
phase = theta + np.pi / 2
```

Avoid comments such as:

```python
# Increment i
i += 1
```

Comments should document:

- Non-obvious algorithms.
- Mathematical reasoning.
- Coordinate-system conventions.
- Workarounds.
- Important assumptions.
- Reasons for apparently unusual implementation choices.
- Constraints imposed by external libraries or file formats.

Comments must be updated when the associated code changes.

---

## 7. Constants and Magic Values

Avoid unexplained numeric or string literals embedded in code.

Prefer named constants:

```python
DEFAULT_RING_POINTS = 64
MINIMUM_RADIUS = 0.001
```

rather than:

```python
points = 64
```

Values which are genuinely local and obvious do not need to be converted into constants unnecessarily.

---

## 8. Error Handling

Do not silently suppress exceptions.

Avoid:

```python
try:
    ...
except Exception:
    pass
```

Catch the narrowest appropriate exception type.

Where an error is recoverable, handle it explicitly.

Where an error indicates invalid program state or invalid caller input, raise a meaningful exception with an informative message.

For example:

```python
if chamber_spacing <= 0:
    raise ValueError("chamber_spacing must be greater than zero")
```

Do not use exceptions as normal control flow where a straightforward conditional would be clearer.

---

## 9. Input Validation

Public functions should validate inputs where invalid values could:

- Produce misleading results.
- Cause obscure downstream errors.
- Corrupt data.
- Produce invalid geometry or state.

Validation should normally occur as close as possible to the public interface.

---

## 10. Data Structures

Use appropriate Python structures rather than relying on loosely structured dictionaries where the structure is known in advance.

Prefer:

- `dataclass` for structured application data.
- `Enum` for fixed sets of meaningful values.
- Typed classes or models for complex configuration.
- Dictionaries for genuinely dynamic key/value data.

For example:

```python
@dataclass
class ShellParameters:
    growth_rate: float
    aperture_radius: float
    turns: float
```

---

## 11. Classes

Classes should represent a coherent concept or responsibility.

Avoid large "god classes" which manage unrelated behaviour.

Prefer composition over deep inheritance hierarchies unless inheritance represents a genuine and stable "is-a" relationship.

Instance attributes should normally be initialised explicitly in `__init__`.

Public class interfaces should be kept small and intentional.

---

## 12. Modules and Packages

Modules should have a clear, coherent purpose.

Avoid placing unrelated utilities into large generic modules such as:

```text
utils.py
helpers.py
misc.py
```

where a more specific module name is possible.

Imports should be grouped as:

1. Python standard library.
2. Third-party libraries.
3. Project-local modules.

For example:

```python
from pathlib import Path

import numpy as np
import pandas as pd

from shell_model.geometry import build_mesh
```

Avoid wildcard imports:

```python
from module import *
```

---

## 13. Global State

Avoid mutable global state.

Configuration should normally be passed explicitly to functions or represented by configuration objects.

Module-level constants are acceptable.

Code should not depend on execution order or hidden state where this can reasonably be avoided.

---

## 14. File and Path Handling

Use `pathlib.Path` rather than manual string concatenation for filesystem paths.

Prefer:

```python
output_path = data_directory / "shells" / filename
```

rather than:

```python
output_path = data_directory + "/shells/" + filename
```

Do not assume a particular current working directory unless this is explicitly part of the application's design.

---

## 15. Logging and Diagnostic Output

Library and application code should not use arbitrary `print()` statements for diagnostic output.

Use Python's `logging` module where persistent or configurable diagnostic output is required.

`print()` is acceptable for:

- Command-line user output.
- Interactive notebooks.
- Temporary development diagnostics which are removed before commit.

---

## 16. Testing

Important computational and business logic should have automated tests.

Tests should cover:

- Normal expected behaviour.
- Boundary conditions.
- Invalid input.
- Previously discovered bugs where regression is possible.

Bug fixes should normally include a regression test when practical.

Tests should be deterministic. Random behaviour should use controlled seeds where necessary.

---

## 17. Numerical Code

Numerical algorithms should document:

- Units.
- Coordinate systems.
- Angle conventions.
- Expected ranges.
- Relevant mathematical assumptions.

Do not mix degrees and radians implicitly.

Where tolerances are required for floating-point comparison, use appropriate numerical comparison methods rather than direct equality.

Prefer:

```python
np.isclose(a, b)
```

rather than:

```python
a == b
```

for calculated floating-point values.

---

## 18. Dependencies

Add third-party dependencies only where they provide a clear benefit.

Prefer the Python standard library where it provides an adequate solution.

Dependencies should be recorded in the project's dependency-management file and, where reproducibility matters, version constraints should be specified.

Do not rely on packages which happen to be installed in a developer's local environment without declaring them as project dependencies.

---

## 19. Jupyter Notebooks

Notebooks should be treated as reproducible project artefacts rather than temporary scratchpads where they form part of the project.

A committed notebook should:

- Run successfully from top to bottom.
- Not depend on cells having been executed in an unusual order.
- Avoid hidden state.
- Contain explanatory Markdown where appropriate.
- Keep substantial reusable logic in Python modules rather than duplicating it across notebooks.
- Avoid retaining large or irrelevant diagnostic outputs.
- Use clear section headings.

Notebook cells should generally perform one logical operation.

Reusable functions developed in notebooks should be moved into project modules once they become part of the project's stable functionality.

---

## 20. Dead and Experimental Code

Do not leave large blocks of commented-out code in committed source files.

Version control is the historical record.

Remove obsolete code rather than commenting it out.

Experimental code which is deliberately retained should be clearly identified and kept separate from production functionality where practical.

---

## 21. TODO Comments

TODO comments should explain both the outstanding work and, where useful, the reason it remains outstanding.

Prefer:

```python
# TODO: Replace linear search with indexed lookup if the catalogue
# grows beyond approximately 10,000 records.
```

rather than:

```python
# TODO: improve this
```

TODOs should not be used as substitutes for documenting known correctness problems.

---

## 22. Code Duplication

Avoid duplicating substantial logic.

Where the same operation appears in multiple places, consider extracting it into a common function or class.

Do not over-generalise prematurely: two superficially similar pieces of code do not necessarily require abstraction.

The aim is to remove duplication of **behaviour**, not merely duplication of syntax.

---

## 23. Public APIs and Backwards Compatibility

Changes to public functions, configuration structures, file formats, or stored data should be considered interface changes.

Where practical:

- Avoid changing established interfaces unnecessarily.
- Document deliberate breaking changes.
- Provide migration paths for persisted data where required.

Internal implementation details may be refactored freely provided observable behaviour remains unchanged.

---

## 24. Formatting and Static Analysis

Code should be automatically formatted rather than relying entirely on manual formatting.

Recommended tooling:

- **Ruff** for linting and import checking.
- **Black** or Ruff's formatter for consistent formatting.
- **pytest** for automated testing.
- A type checker such as **mypy** or **Pyright** where useful.

Formatting and linting should ideally be run automatically before code is committed.

---

## 25. Source Control Hygiene

Commits should represent coherent changes.

Before committing:

- Remove temporary debug output.
- Remove unused imports.
- Remove commented-out obsolete code.
- Run relevant tests.
- Ensure changed notebooks execute correctly where applicable.
- Check that generated files, caches, credentials, and local configuration have not been accidentally added.

Commit messages should describe the purpose of the change rather than merely the files changed.

---

## 26. Security and Secrets

Passwords, API keys, tokens, and other credentials must never be committed to source control.

Secrets should be supplied through an appropriate mechanism such as:

- Environment variables.
- Local configuration excluded by `.gitignore`.
- A secrets-management facility.

Code should not log credentials or sensitive data.

---

## 27. The Readability Test

Before considering code complete, ask:

> Could another developer — or myself six months from now — understand what this code does, why it does it, and how to change it safely?

If not, improve the naming, structure, documentation, or tests before considering the implementation finished.
