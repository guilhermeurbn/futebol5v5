---
name: natrave-agents
description: "Multi-specialist team of agents for NaTrave 5v5 development, design, testing, and architecture."
---

# NaTrave 5v5 Agent Team

This workspace includes specialized agents for different aspects of the project. Choose the right agent for your task:

## 🎨 **Design Agent** (`@design-agent`)
**Focus:** UI/UX, Styling, Responsiveness, Accessibility

- Review and improve CSS and design system
- Fix layout issues and visual consistency
- Optimize responsive design
- Ensure WCAG accessibility compliance
- Enhance user experience through better layouts
- Work with color schemes, typography, and spacing

**When to use:** "The layout is breaking on mobile", "Fix the button positioning", "Improve the design system", "Make the page more accessible"

---

## 🧪 **Tester Agent** (`@tester-agent`)
**Focus:** QA, Testing, Bug Detection, Validation

- Write and execute test cases
- Identify bugs and edge cases
- Validate forms and user interactions
- Test responsive design across devices
- Check for security vulnerabilities
- Perform regression testing
- Document test results and issues

**When to use:** "Test this feature", "Find bugs in the login flow", "Write tests for this", "Check for security issues"

---

## 🏗️ **Architect Agent** (`@architect-agent`)
**Focus:** System Design, Code Organization, Patterns, Scalability

- Design scalable system architecture
- Define and enforce design patterns
- Plan database schema improvements
- Improve code modularity and organization
- Plan performance optimizations
- Document architectural decisions
- Plan PWA and offline enhancements

**When to use:** "How should we structure this feature?", "Refactor the code organization", "Design a new component", "Improve the system architecture"

---

## 👨‍💻 **Developer Agent** (`@developer-agent`)
**Focus:** Implementation, Feature Development, Bug Fixes, Code Quality

- Implement new features and user stories
- Fix bugs and issues
- Refactor code for readability and performance
- Write clean, maintainable code
- Update frontend components and templates
- Optimize code performance
- Keep dependencies secure

**When to use:** "Implement this feature", "Fix this bug", "Refactor this code", "Add new functionality"

---

## ⚡ **Performance Agent** (`@performance-agent`)
**Focus:** Optimization, Speed, Caching, Load Times

- Identify performance bottlenecks
- Optimize database queries and operations
- Implement caching strategies
- Reduce load times and bundle size
- Optimize API response times
- Profile application for slow operations
- Monitor performance metrics

**When to use:** "The app is too slow", "Optimize this query", "Implement caching", "Improve page load time"

---

## Workflow Examples

### Implementing a New Feature
1. **Architect**: Design the feature structure
2. **Developer**: Implement the feature
3. **Tester**: Test and validate
4. **Design**: Polish the UI/UX
5. **Performance**: Optimize if needed

### Fixing a Bug
1. **Tester**: Identify and report the bug
2. **Developer**: Fix the bug
3. **Tester**: Verify the fix
4. **Design**: Check UI impact if relevant
5. **Performance**: Check performance impact if relevant

### Performance Optimization
1. **Performance**: Identify bottlenecks
2. **Architect**: Plan optimizations
3. **Developer**: Implement optimizations
4. **Tester**: Validate improvements
5. **Performance**: Measure and report gains

### Design Improvements
1. **Design**: Identify issues and propose improvements
2. **Developer**: Implement changes
3. **Tester**: Test responsive design
4. **Performance**: Check impact on load times

---

## Current Project Context

**Project:** NaTrave 5v5 - Futebol Team Balancer  
**Stack:** Python/Flask + HTML/CSS/JavaScript  
**Key Features:**
- Player selection and team balancing
- Match management and voting
- Offline PWA support
- User authentication and roles
- Admin dashboard and statistics

**Key Services:**
- `services/auth_service.py` - Authentication
- `services/balanceamento.py` - Team balancing
- `services/partida_service.py` - Match management
- `services/votacao_service.py` - Voting system
- `routes/jogador_routes.py` - API endpoints
- `templates/` - Frontend pages
- `static/style.css` - Styling system
