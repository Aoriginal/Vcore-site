# Skills Library

Reusable skills, templates, and components for the agent system.

## Structure

```
Skills/
├── README.md           ← This file
├── Shared/             ← Skills any agent can use
│   ├── README.md
│   ├── research-template.md
│   ├── task-brief-template.md
│   └── status-report-template.md
└── ComponentLibrary/   ← Reusable code and build components
    ├── README.md
    └── (components added by Lamar as builds complete)
```

## How to Add a Skill

1. Create a `.md` file in the appropriate folder
2. Use the format: `# Skill Name`, `## When to Use`, `## How to Use`, `## Template`
3. Reference it in the relevant agent's memory file under "Skills"

## Guidelines

- Skills should be atomic — one clear purpose each
- Include an example showing correct usage
- Update when you discover a better approach
