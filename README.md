# define-cli

CLI vocabulary lookup for language learners. Fetches definitions, IPA pronunciation, and real usage examples.

## Install

```bash
pip install define-cli
```

## Usage

```bash
define fr bonjour          # IPA + definitions + 5 examples
define nl ingewikkeld
define fr bonjour -e       # full examples dump from Reverso
define fr bonjour --no-reverso   # definitions only
define fr bonjour --no-wikt      # examples only
```

## Supported languages

| Code | Language   |
|------|------------|
| fr   | French     |
| nl   | Dutch      |
| de   | German     |
| es   | Spanish    |
| it   | Italian    |
| pt   | Portuguese |

## Sources

- **English Wiktionary** — IPA, part of speech, definitions
- **Reverso Context** — real-world usage examples with translations

## Development

```bash
git clone https://github.com/mbeardwell/define-cli
cd define-cli
pip install -e ".[dev]"
```
