# define-cli

CLI vocabulary lookup for language learners. Fetches definitions, IPA pronunciation, and real usage examples.

## Install
```bash
pipx install git+https://github.com/abbyslab/define-cli
```

## Usage
```bash
define fr bonjour          # IPA + definitions + 5 examples
define nl ingewikkeld
define fr bonjour -e       # full examples dump
define fr bonjour --no-reverso   # definitions only
define fr bonjour --no-wikt      # examples only
```

## Supported languages

| Code | Language   |
|------|------------|
| ar   | Arabic     |
| ca   | Catalan    |
| zh   | Chinese    |
| cs   | Czech      |
| da   | Danish     |
| nl   | Dutch      |
| fr   | French     |
| de   | German     |
| el   | Greek      |
| he   | Hebrew     |
| hi   | Hindi      |
| hu   | Hungarian  |
| it   | Italian    |
| ja   | Japanese   |
| ko   | Korean     |
| fa   | Persian    |
| pl   | Polish     |
| pt   | Portuguese |
| ro   | Romanian   |
| ru   | Russian    |
| sk   | Slovak     |
| es   | Spanish    |
| sv   | Swedish    |
| th   | Thai       |
| tr   | Turkish    |
| uk   | Ukrainian  |
| vi   | Vietnamese |

## Sources

- **English Wiktionary** — IPA, part of speech, definitions
- **Reverso Context** — real-world usage examples with translations
- **Tatoeba** — fallback examples for languages not supported by Reverso

## Development
```bash
git clone git@github.com:abbyslab/define-cli
cd define-cli
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```
