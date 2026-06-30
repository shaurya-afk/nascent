# Nascent

Nascent is an AI software engineering agent that understands an existing codebase, plans changes, generates production-ready code, presents diffs for human approval, and automatically creates Git commits and pull requests.

## Features

- Repository-aware code generation
- Intelligent repository indexing and caching
- Planning before code generation
- Human-in-the-loop approval workflow
- Context-aware code modifications
- Git diff generation
- Git commit automation
- Automatic branch creation
- GitHub App authentication
- Automatic push to GitHub
- Pull request creation
- Multi-user GitHub App support

## Workflow

```text
Repository URL
      │
      ▼
Load Cached Repository
      │
      ├── Cache Hit
      │        │
      │        ▼
      │     Planning
      │
      └── Cache Miss
               │
               ▼
        Clone Repository
               │
               ▼
        Repository Extraction
               │
               ▼
        Store Repository Index
               │
               ▼
            Planning
               │
               ▼
      Human Approval (Plan)
               │
               ▼
        Context Loading
               │
               ▼
        Code Generation
               │
               ▼
            Git Diff
               │
               ▼
      Human Approval (Diff)
               │
               ▼
          Git Commit
               │
               ▼
          Git Push
               │
               ▼
      Create Pull Request
```

## Tech Stack

- Python
- FastAPI
- LangGraph
- PostgreSQL
- SQLAlchemy
- GitPython
- GitHub App
- GitHub OAuth
- OpenRouter
- NeonDB

## Current Capabilities

- Authenticate users with GitHub OAuth
- Connect repositories using GitHub Apps
- Cache repository summaries
- Generate implementation plans
- Human approval before generation
- Modify existing codebases
- Generate Git diffs
- Commit changes
- Push branches
- Open Pull Requests automatically

## Roadmap

- Streaming agent execution
- Repository-wide semantic search
- Parallel code generation
- Multi-file editing improvements
- Test generation
- Automatic code review
- CI status integration
- Issue-driven development
- Web-based workspace
- Team collaboration

## License

MIT