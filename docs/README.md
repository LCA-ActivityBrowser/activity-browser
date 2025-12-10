# docs

Documentation for Activity Browser.

## Overview

This directory contains the source files for Activity Browser's documentation website, which is built using Jekyll and hosted on GitHub Pages.

## Structure

- **Jekyll Site Configuration**
  - `_config.yml` - Jekyll site configuration
  - `Gemfile` - Ruby gem dependencies
  - `404.html` - Custom 404 error page
  - `index.md` - Documentation homepage

- **`_includes/`** - Reusable HTML/Liquid templates
  - `nav_footer_custom.html` - Custom navigation footer
  - `search_placeholder_custom.html` - Custom search placeholder

- **`_sass/`** - SASS/CSS stylesheets
  - `custom/` - Custom styling overrides

- **`getting-started/`** - Getting started guides
  - `installation.md` - Installation instructions
  - `project-setup.md` - Setting up your first project
  - `creating-databases.md` - Creating and managing databases
  - `building-models.md` - Building LCA models
  - `lca-calculations.md` - Running LCA calculations
  - `index.md` - Getting started overview

- **`user-interface/`** - UI documentation
  - `pages/` - Documentation for each page
  - `index.md` - UI overview

- **`advanced-topics/`** - Advanced features
  - `project-structure.md` - Understanding project structure
  - `scenario-calculations.md` - Scenario analysis
  - `brightway-legacy.md` - Working with Brightway legacy versions
  - `multifunctional-databases/` - Multi-functionality documentation
  - `index.md` - Advanced topics overview

- **`assets/`** - Images, screenshots, and other assets

- **`beta.md`** - Beta version information

## Building Documentation

### Prerequisites
- Ruby (for Jekyll)
- Bundler gem

### Local Development

1. Install dependencies:
   ```bash
   cd docs
   bundle install
   ```

2. Serve locally:
   ```bash
   bundle exec jekyll serve
   ```

3. View at: `http://localhost:4000`

### Live Documentation

The documentation is automatically built and deployed to GitHub Pages when changes are pushed to the repository.

URL: [https://lca-activitybrowser.github.io/activity-browser/](https://lca-activitybrowser.github.io/activity-browser/)

## Writing Documentation

### Markdown Files

Documentation is written in Markdown with Jekyll front matter:

```markdown
---
layout: default
title: Page Title
nav_order: 1
---

# Page Title

Content goes here...
```

### Front Matter Options

- **`layout`** - Page layout template (usually `default`)
- **`title`** - Page title
- **`nav_order`** - Navigation menu order
- **`parent`** - Parent page for nested navigation
- **`has_children`** - Whether page has child pages
- **`permalink`** - Custom URL path

### Linking Pages

Use relative links:
```markdown
See [Installation Guide]({% link getting-started/installation.md %})
```

### Including Images

Place images in `assets/` and reference:
```markdown
![Screenshot](../assets/screenshot.png)
```

### Code Blocks

Use fenced code blocks with language:
```markdown
```python
import bw2data as bd
bd.projects.set_current("my_project")
```
```

## Documentation Structure

### Getting Started
Target audience: New users
- Installation
- First project
- Basic concepts
- First calculation

### User Interface
Target audience: All users
- Navigation
- Pages and panes
- Common tasks
- Keyboard shortcuts

### Advanced Topics
Target audience: Power users
- Scenarios and parameters
- Uncertainty analysis
- Sensitivity analysis
- Multi-functionality
- Integration with Brightway

## Style Guide

### Writing Style
- **Clear and concise** - Simple language
- **Task-oriented** - Focus on what users want to do
- **Step-by-step** - Break down complex tasks
- **Visual aids** - Screenshots and diagrams
- **Examples** - Show real examples

### Formatting
- **Headings** - Use proper hierarchy (H1, H2, H3)
- **Lists** - For steps or multiple items
- **Bold** - For UI elements and important terms
- **Code** - For code, commands, and file paths
- **Notes/Tips** - Use blockquotes for callouts

### Screenshots
- Use actual application screenshots
- Highlight relevant areas
- Keep up-to-date with current UI
- Crop to show only relevant content
- Use consistent window size

## Maintenance

### Keeping Current
- Update screenshots when UI changes
- Verify instructions after code changes
- Add documentation for new features
- Mark deprecated features
- Update version numbers

### Review Process
- Test instructions on fresh install
- Check all links work
- Verify code examples
- Review for clarity
- Check mobile responsiveness

## Contributing

To contribute to documentation:

1. Fork the repository
2. Create a branch for your changes
3. Edit/add Markdown files in `docs/`
4. Test locally with Jekyll
5. Submit a pull request

See [CONTRIBUTING.md](../CONTRIBUTING.md) for more details.

## Resources

- [Jekyll Documentation](https://jekyllrb.com/docs/)
- [Just the Docs Theme](https://just-the-docs.github.io/just-the-docs/)
- [Markdown Guide](https://www.markdownguide.org/)
- [GitHub Pages](https://pages.github.com/)
