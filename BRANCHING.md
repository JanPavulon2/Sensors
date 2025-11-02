# Git Branching Strategy

## Overview

This project uses a **version-based branching strategy** with three levels of branches:

```
main (production-ready releases)
  └── version/X.Y (version in development)
      └── feature/feature-name (individual features)
```

## Branch Hierarchy

### 1. `main` Branch
- **Purpose**: Production-ready code only
- **Protection**: Protected branch, requires PR review
- **Updates**: Only receives merges from completed `version/X.Y` branches
- **Naming**: `main` (default branch)

### 2. Version Branches
- **Purpose**: Container for multiple features that together form a version release
- **Lifetime**: Created at start of version, merged to `main` when version complete
- **Naming**: `version/X.Y` (e.g., `version/0.1`, `version/0.2`, `version/1.0`)
- **Base**: Created from `main`
- **Updates**: Receives merges from completed feature branches

### 3. Feature Branches
- **Purpose**: Development of individual features
- **Lifetime**: Created for feature, deleted after merge to version branch
- **Naming**: `feature/feature-name` (e.g., `feature/events`, `feature/animations-advanced`)
- **Base**: Created from current `version/X.Y` branch
- **Updates**: Merged into parent `version/X.Y` branch when complete

## Workflow

### Starting a New Version

```bash
# From main branch
git checkout main
git pull origin main

# Create new version branch
git checkout -b version/0.2
git push -u origin version/0.2
```

### Working on a Feature

```bash
# From version branch
git checkout version/0.1
git pull origin version/0.1

# Create feature branch
git checkout -b feature/my-feature
git push -u origin feature/my-feature

# ... work on feature, commit changes ...

# When feature is complete
git checkout version/0.1
git merge feature/my-feature --no-ff -m "Merge feature/my-feature: Description"
git push origin version/0.1

# Delete feature branch (optional)
git branch -d feature/my-feature
git push origin --delete feature/my-feature
```

### Completing a Version

When all features for a version are complete and tested:

```bash
# From version branch
git checkout version/0.1
git push origin version/0.1

# Merge to main
git checkout main
git pull origin main
git merge version/0.1 --no-ff -m "Release version 0.1"
git push origin main

# Tag the release
git tag -a v0.1 -m "Version 0.1: Description of changes"
git push origin v0.1
```

## Version Numbering

Follow semantic versioning: `MAJOR.MINOR.PATCH`

- **MAJOR** (1.0, 2.0): Breaking changes, major architecture changes
- **MINOR** (0.1, 0.2, 1.1): New features, non-breaking changes
- **PATCH** (0.1.1, 0.1.2): Bug fixes, minor tweaks

For this project (currently in early development):
- Start with `0.1`, `0.2`, etc.
- Move to `1.0` when API is stable and feature-complete

## Benefits of This Strategy

1. **Clean main branch**: Only production-ready code
2. **Grouped features**: Related features bundled in versions
3. **Easy rollback**: Can revert entire versions if needed
4. **Clear releases**: Each version branch = one release
5. **Parallel development**: Multiple features can be developed simultaneously
6. **Testing checkpoint**: Test all features together before merging to main

## Current Version

- **Active version branch**: `version/0.1`
- **Features included**:
  - Event system (EventBus, middleware)
  - Transition system (crossfades, fades)
  - Animation improvements (breathe per-zone, preview crossfades)
  - Disabled zone fix (preserve pixel indices)

## Migration from Old Strategy

**Old strategy**: `main` ← `feature/X` (direct merge)

**New strategy**: `main` ← `version/X.Y` ← `feature/X`

All existing feature branches should be merged to `version/0.1` first, then `version/0.1` will be merged to `main` when ready.
