# WorkIQ Showcase

A Streamlit showcase app for demonstrating WorkIQ through a clean, chat-first experience.

## What this app does

This app is being built to show how WorkIQ can:

- understand work context such as meetings, priorities, stakeholders, and conflicts
- continue from earlier context using memory
- generate practical outputs such as draft messages
- surface productivity insights and recommended actions

The experience is intentionally lightweight:
- chat-first main screen
- sidebar quick starts
- memory toggle
- WorkIQ CLI connection settings
- live diagnostic to verify the CLI is working

## How to run this repo

From the project root:

```bash
pip install -r requirements.txt
streamlit run app.py