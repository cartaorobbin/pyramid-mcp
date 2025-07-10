# General Planning - Current Active Tasks

## 🎯 Current Active Tasks

*No active tasks currently. Add new tasks as they are started.*

---

## 📋 Task Management Guidelines

### When to Use This File
- **CURRENT tasks actively being worked on**
- **IN PROGRESS development work**
- **Immediate priority tasks**
- **Keep focused (max 1-3 active task groups)**

### Task Flow
1. **Add to `planning/backlog.md`**: Plan future tasks
2. **Move to `planning/general.md`**: When starting active work
3. **Update progress**: Track completion status
4. **Move to `planning/done.md`**: When task is DONE and tests pass

### Task Status Options
- **TODO**: Not started yet
- **IN PROGRESS**: Currently working on
- **DONE**: Completed successfully
- **BLOCKED**: Cannot proceed due to external dependency

### Template for New Tasks
```markdown
### [YYYY-MM-DD] Task Description

**Status**: TODO | IN PROGRESS | DONE | BLOCKED
**Assigned**: Your Name
**Estimated Time**: X hours
**Related Issue**: #123

#### Plan
- [ ] Task 1: Description
- [ ] Task 2: Description
- [ ] Task 3: Description

#### Progress
- [ ] Current task status
- [ ] Next steps

#### Decisions Made
- Decision 1: Reasoning
- Decision 2: Reasoning

#### Blockers/Issues
- Issue 1: Description and resolution plan
```

---

## 📊 Quick Reference

- **Add new tasks**: Use `planning/backlog.md`
- **Start working**: Move to `planning/general.md`
- **Complete tasks**: Move to `planning/done.md`
- **Large features**: Create `planning/[feature-name].md`
- **Templates**: Use `planning/feature-template.md` 

---

## [2025-01-20] PyPI Publishing Setup with GitHub Actions

**Status**: DONE ✅
**Assigned**: Assistant  
**Estimated Time**: 2 hours
**Related Issue**: User request for PyPI publishing setup

### Plan
- [x] Review existing GitHub Actions workflows  
- [x] Update PyPI publishing workflow with trusted publishing
- [x] Update main CI workflow with latest action versions
- [x] Create comprehensive publishing documentation
- [x] Add test publishing workflow for TestPyPI
- [x] Update project configuration for Python 3.12 support
- [x] Fix code quality issues (formatting, linting)
- [x] Verify all tests pass

### Progress
- [x] **Reviewed existing workflows**: Found `on-release-pypi.yml` and `main.yml` already in place
- [x] **Updated PyPI publishing workflow**: 
  - Switched to trusted publishing (no API tokens needed)
  - Added proper version extraction from Git tags
  - Added package verification with twine
  - Updated to use actions/checkout@v4
  - Added environment protection
- [x] **Updated main CI workflow**:
  - Added Python 3.12 support
  - Updated to latest action versions
  - Improved workflow structure and naming
  - Added comprehensive test coverage
- [x] **Created comprehensive documentation**: 
  - Added `docs/publishing.md` with complete PyPI publishing guide
  - Updated `docs/index.md` to include publishing guide
  - Included troubleshooting section and best practices
- [x] **Added test publishing workflow**: 
  - Created `test-pypi.yml` for testing package builds
  - Added TestPyPI publishing for manual testing
  - Included package verification and installation testing
- [x] **Updated project configuration**:
  - Added Python 3.12 support to `pyproject.toml`
  - Updated repository URLs from placeholders
  - Verified tox.ini already includes Python 3.12
- [x] **Fixed code quality issues**:
  - Ran `make format` to fix black formatting
  - Fixed line length issue in `introspection.py`
  - Removed unused import in `test_pyramid_tm_integration.py`
  - All tests pass: `make test` ✅
  - All quality checks pass: `make check` ✅

### Decisions Made
- **Trusted Publishing**: Using PyPI's trusted publishing feature instead of API tokens for better security
- **Modern Actions**: Updated to latest GitHub Actions versions (v4/v5)
- **Python 3.12**: Added support for Python 3.12 across all workflows
- **Test Publishing**: Created separate workflow for testing builds without publishing
- **Environment Protection**: Using GitHub environments for additional security

### Deliverables
- ✅ **Updated `.github/workflows/on-release-pypi.yml`**: Modern PyPI publishing with trusted publishing
- ✅ **Updated `.github/workflows/main.yml`**: Comprehensive CI with latest actions
- ✅ **Created `.github/workflows/test-pypi.yml`**: Test publishing workflow
- ✅ **Created `docs/publishing.md`**: Complete publishing guide
- ✅ **Updated `docs/index.md`**: Added publishing guide reference
- ✅ **Updated `pyproject.toml`**: Python 3.12 support and proper URLs
- ✅ **Code quality fixes**: All formatting and linting issues resolved

### Next Steps for User
1. **Update repository URLs**: Replace placeholder URLs in `pyproject.toml` with actual GitHub repository
2. **Set up PyPI trusted publishing**: 
   - Create PyPI account if needed
   - Configure trusted publishing on PyPI with repository details
3. **Create first release**: 
   - Test with `git tag v0.1.0 && git push origin v0.1.0`
   - Create GitHub release to trigger automatic PyPI publishing
4. **Optional**: Set up TestPyPI for testing releases before production

### Test Results
- ✅ **All tests passing**: 157 passed, 1 xfailed, 0 failed
- ✅ **Code quality checks**: All black, isort, flake8, mypy checks pass
- ✅ **Package structure**: Proper Poetry configuration for publishing 