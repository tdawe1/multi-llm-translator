# Changelog

## [1.0.0] - 2025-07-31

### Added

- Initial release of the Multi-LLM Translation Assistant.
- Interactive web UI (Streamlit) for real-time configuration, job monitoring, and translation comparison.
- Headless background service for automated job processing.
- Support for multiple LLMs: GPT, Claude, and Gemini.
- Processing of `.docx`, `.pptx`, and `.xlsx` documents.
- Multiple workflow modes: `SIMPLE`, `PARALLEL`, and `CRITIQUE`.
- Glossary support for consistent terminology.
- Live configuration reload without service restart.
- Automated job monitoring via CSV file or a "hot folder".
- Colored logging for console and detailed `app.log`.
- Integration with GengoWatcher-Public.
- Recommended `systemd` service setup for production use.
