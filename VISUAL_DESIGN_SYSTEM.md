# 🎨 LogoForge AI - Visual Design Reference

## Color Palette

### Primary Colors
```
Primary Gradient: #667eea → #764ba2
Primary: #667eea (Royal Blue)
Secondary: #764ba2 (Deep Purple)
```

### Secondary Colors
```
Success: #52c41a (Green)
Info: #1890ff (Blue)
Warning: #faad14 (Amber)
Error: #ff4d4f (Red)
```

### Neutral Colors
```
Background: #f5f7fa (Light Blue-Gray)
Text: #2d3748 (Dark Gray)
Text Light: #718096 (Medium Gray)
Border: #e2e8f0 (Light Gray)
White: #ffffff
```

## Generator Badges

### DALL-E 3
```
Gradient: #f093fb → #f5576c (Pink to Red)
Text: White
Icon: 🎨
```

### Gemini
```
Gradient: #4facfe → #00f2fe (Blue to Cyan)
Text: White
Icon: ✨
```

## Typography

### Font Families
```
Primary: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto'
Fallback: Sans-serif
```

### Font Weights
```
Regular: 400
Medium: 500
Semibold: 600
Bold: 700
Extra Bold: 800
```

### Font Sizes
```
Body: 0.95rem (15.2px)
Label: 0.9rem (14.4px)
Small: 0.85rem (13.6px)
Large: 1.1rem (17.6px)
XL: 1.3rem (20.8px)
2XL: 1.5rem (24px)
3XL: 2.8rem (44.8px)
```

## Spacing Scale

```
xs: 0.25rem (4px)
sm: 0.5rem (8px)
md: 1rem (16px)
lg: 1.5rem (24px)
xl: 2rem (32px)
2xl: 2.5rem (40px)
3xl: 3rem (48px)
```

## Border Radius

```
Small: 0.5rem (8px)
Medium: 0.75rem (12px) - DEFAULT
Large: 1rem (16px)
```

## Shadows

### Card Shadow
```
box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08)
```

### Hover Shadow
```
box-shadow: 0 12px 35px rgba(0, 0, 0, 0.12)
```

### Button Shadow
```
box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3)
```

### Button Hover Shadow
```
box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4)
```

## Component Sizes

### Buttons
```
Regular: 45px height
Small: 36px height
Padding: 0.95rem 2rem
Small Padding: 0.6rem 1.2rem
```

### Cards
```
Padding: 2rem
Border: 1px solid #e8eef7
Radius: 1rem
```

### Input Fields
```
Height: 40px (auto)
Padding: 0.75rem 1rem
Border: 2px solid #e2e8f0
Radius: 0.75rem
```

## Animations

### Transitions
```
Default Duration: 0.3s
Easing: ease
Property: all
```

### Hover Effects
```
Button: translateY(-3px) + shadow increase
Card: translateY(-2px) + shadow increase
Input Focus: Border color + glow
```

### Animations
```
Slide Down: 0.6s ease (header entrance)
Spin: 1s linear infinite (loading spinner)
```

## Breakpoints

### Responsive Design
```
Mobile: < 768px
Tablet: 768px - 1024px
Desktop: > 1024px
```

## Layout Dimensions

### Two-Column Layout (Generate Tab)
```
Form Column: 55-60% width
Tips Column: 40-45% width
Gap: 1.5rem
```

### Three-Column Layout (Preview)
```
Each Column: ~33.33% width
Gap: 1.5rem
Min Width: 250px (responsive)
```

### Max Width
```
Container: 1400px
Form: 700px
Card: unlimited (responsive)
```

## Accessibility

### Contrast Ratios
```
Text on Background: 4.5:1 (WCAG AA)
Large Text: 3:1 (WCAG AA)
UI Components: 3:1 (WCAG AA)
```

### Focus States
```
Border Color: Change to primary
Box Shadow: 0 0 0 3px rgba(102, 126, 234, 0.1)
Outline: None (custom focus)
```

## Form Styling

### Input States

**Normal**
```
Border: 2px solid #e2e8f0
Background: white
Color: #2d3748
```

**Focus**
```
Border Color: #667eea
Box Shadow: 0 0 0 3px rgba(102, 126, 234, 0.1)
```

**Error**
```
Border Color: #ff4d4f
Background: #fff1f0
```

**Disabled**
```
Opacity: 0.5
Cursor: not-allowed
```

## Message Styling

### Success
```
Background: #f6ffed
Border Left: 4px solid #52c41a
Color: #155724
```

### Info
```
Background: #e6f7ff
Border Left: 4px solid #1890ff
Color: #0050b3
```

### Warning
```
Background: #fffbe6
Border Left: 4px solid #faad14
Color: #664d03
```

### Error
```
Background: #fff1f0
Border Left: 4px solid #ff4d4f
Color: #5c1114
```

## Badge Styles

### Primary Badge
```
Background: rgba(102, 126, 234, 0.15)
Color: #667eea
```

### Success Badge
```
Background: rgba(82, 196, 26, 0.15)
Color: #52c41a
```

### Info Badge
```
Background: rgba(24, 144, 255, 0.15)
Color: #1890ff
```

### Generator Badges
```
DALL-E 3: Gradient pink-to-red
Gemini: Gradient blue-to-cyan
Box Shadow: 0 4px 15px with badge color
```

## Code Block Styling

### Code Container
```
Background: #2d3748 (Dark Gray)
Color: #e2e8f0 (Light Text)
Padding: 1rem
Border Radius: 0.75rem
Font Family: monospace
```

## Responsive Behaviors

### Mobile (< 768px)
```
Columns: Stack to 1 column
Padding: 1rem
Font Size: Slightly reduced
Buttons: Full width
```

### Tablet (768px - 1024px)
```
Two Column: 50% - 50%
Padding: 1.5rem
Normal font sizing
```

### Desktop (> 1024px)
```
Two Column: 55% - 45%
Padding: 2.5rem
Full sized buttons
Max width constraints
```

## Interactive Elements

### Buttons

**Primary Button**
- Gradient background
- White text
- Bold font (700)
- Hover: Lift up (-3px) + shadow
- Active: Subtle press (active state)
- Disabled: Opacity 0.5

**Secondary Button**
- Light background (#f7fafc)
- Gray text
- Hover: Darker background
- Disabled: Opacity 0.5

### Select / Dropdown
- 2px border
- Focus glow like inputs
- Smooth transitions
- Increased touch target

## Animation Timings

```
Fast: 0.15s
Normal: 0.3s (default)
Slow: 0.6s
Very Slow: 1s
```

## Z-Index Scale

```
Base: 0
Elevated: 10
Modal/Overlay: 50
Tooltip: 100
```

## Design System Usage

### When to Use Each Color

**Primary (#667eea)**
- Call-to-action buttons
- Active states
- Links
- Important highlights

**Secondary (#764ba2)**
- Gradients
- Complementary highlights
- Badges

**Success (#52c41a)**
- Positive confirmations
- Success messages
- Check marks

**Info (#1890ff)**
- Informational content
- Help text
- Notifications

**Warning (#faad14)**
- Warnings
- Cautions
- Alert messages

**Error (#ff4d4f)**
- Error states
- Validation failures
- Destructive actions

---

## Implementation Notes

All colors and sizes are defined as CSS variables in `:root`:

```css
:root {
    --primary: #667eea;
    --secondary: #764ba2;
    --bg: #f5f7fa;
    --card-bg: #ffffff;
    --text: #2d3748;
    --text-light: #718096;
    --border: #e2e8f0;
    --success: #52c41a;
    --info: #1890ff;
    --warning: #faad14;
    --error: #ff4d4f;
}
```

This allows for easy theme switching and maintenance.

---

## Quick Reference Commands

### Running the App
```bash
streamlit run streamlit_app.py
```

### Customizing Colors
Edit the `:root` variables in `style.css`

### Adding New Components
1. Add HTML in `streamlit_app.py`
2. Add CSS in `style.css`
3. Use consistent spacing and colors
4. Test responsive behavior

