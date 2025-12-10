# web

Web views for HTML-based visualizations and interactive content.

## Overview

This directory contains components for embedding web content within Activity Browser using Qt's WebEngine. These web views enable rich, interactive visualizations using HTML, CSS, and JavaScript.

## Purpose

Web views provide:
- **Interactive visualizations** - Sankey diagrams, force-directed graphs, trees
- **Rich content** - HTML-formatted reports and documentation
- **JavaScript libraries** - D3.js, Plotly, Cytoscape.js, etc.
- **External content** - Embedded web pages and resources

## Qt WebEngine

Activity Browser uses `QWebEngineView` (via qtpy):
- Chromium-based rendering engine
- Full HTML5, CSS3, JavaScript support
- Communication between Python and JavaScript
- Secure isolated context

## Common Use Cases

### Graph Visualizations
Force-directed graphs showing activity relationships:
- Node positioning algorithms
- Interactive exploration
- Zoom and pan
- Node/edge highlighting

### Sankey Diagrams
Flow visualizations for LCA results:
- Material/energy flows
- Contribution analysis
- Interactive filtering
- Export to image

### Tree Navigators
Hierarchical data exploration:
- Collapsible tree structures
- Search and filter
- Click to expand/collapse
- Path highlighting

### Charts and Plots
Interactive data visualization:
- Line charts
- Bar charts
- Scatter plots
- Heatmaps
- Custom visualizations

## Architecture

### Python Side
```python
from qtpy.QtWebEngineWidgets import QWebEngineView
from qtpy.QtCore import QUrl

class MyWebView(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.load_content()
        
    def load_content(self):
        # Load from file
        html_path = Path(__file__).parent / "template.html"
        self.setUrl(QUrl.fromLocalFile(str(html_path)))
        
    def send_data_to_js(self, data):
        # Execute JavaScript
        js_code = f"updateData({json.dumps(data)});"
        self.page().runJavaScript(js_code)
```

### JavaScript Side
```javascript
// In HTML template
function updateData(data) {
    // Process data from Python
    renderVisualization(data);
}

// Send data to Python (via callback)
function notifyPython(message) {
    // Setup bridge or use callback mechanism
}
```

## Python-JavaScript Communication

### Python → JavaScript
Execute JavaScript from Python:
```python
self.page().runJavaScript("updateChart(data);")
```

With callback:
```python
def handle_result(result):
    print(f"JavaScript returned: {result}")

self.page().runJavaScript("getData();", handle_result)
```

### JavaScript → Python
Via `QWebChannel` (recommended):

Python:
```python
from qtpy.QtWebChannel import QWebChannel
from qtpy.QtCore import QObject, pyqtSlot

class Bridge(QObject):
    @pyqtSlot(str)
    def receive_message(self, message):
        print(f"Received: {message}")

channel = QWebChannel()
bridge = Bridge()
channel.registerObject("bridge", bridge)
self.page().setWebChannel(channel)
```

JavaScript:
```javascript
new QWebChannel(qt.webChannelTransport, function(channel) {
    var bridge = channel.objects.bridge;
    bridge.receive_message("Hello from JavaScript");
});
```

## HTML Templates

Templates are stored in `activity_browser/static/`:
- `activity_graph.html` - Activity relationship graphs
- `sankey_navigator.html` - Sankey diagrams
- `tree_navigator.html` - Tree structures
- `navigator.html` - Base navigator template

### Template Structure
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Visualization</title>
    <link rel="stylesheet" href="css/styles.css">
    <script src="javascript/d3.min.js"></script>
</head>
<body>
    <div id="visualization"></div>
    <script src="javascript/main.js"></script>
</body>
</html>
```

## JavaScript Libraries

Common libraries used:
- **D3.js** - Data-driven visualizations
- **Cytoscape.js** - Graph visualization and analysis
- **Plotly** - Interactive charts
- **vis.js** - Network and timeline visualizations
- **Sigma.js** - Graph rendering

## Loading Content

### From File
```python
from pathlib import Path
from qtpy.QtCore import QUrl

html_file = Path(__file__).parent / "static" / "graph.html"
self.setUrl(QUrl.fromLocalFile(str(html_file)))
```

### From String
```python
html_content = """
<!DOCTYPE html>
<html>
<body>
    <h1>Hello World</h1>
</body>
</html>
"""
self.setHtml(html_content)
```

### From URL
```python
self.setUrl(QUrl("https://example.com"))
```

## Development Guidelines

When creating web views:

1. **Use templates** - Store HTML in static/ directory
2. **Isolate code** - Separate HTML, CSS, JavaScript files
3. **Handle loading** - Show spinner while content loads
4. **Error handling** - Handle JavaScript errors gracefully
5. **Responsive design** - Handle window resizing
6. **Secure content** - Validate external resources
7. **Performance** - Optimize for large datasets
8. **Testing** - Test in actual web view (not just browser)
9. **Communication** - Use QWebChannel for Python↔JS
10. **Documentation** - Document expected data format

## Data Transfer

### Sending Large Data
For large datasets, consider:
- JSON serialization
- Chunked transfer
- Data compression
- Lazy loading

```python
import json

def send_data(self, data):
    json_data = json.dumps(data)
    js_code = f"loadData({json_data});"
    self.page().runJavaScript(js_code)
```

### Receiving Data
```python
def request_data(self):
    def callback(result):
        data = json.loads(result)
        self.process_data(data)
    
    self.page().runJavaScript("getData();", callback)
```

## Performance Optimization

### Large Datasets
- Render subsets (pagination, windowing)
- Use canvas instead of SVG for many elements
- Implement level-of-detail
- Cache rendered content

### Interactions
- Debounce frequent events
- Throttle animations
- Use requestAnimationFrame
- Optimize DOM manipulation

## Debugging

### JavaScript Console
Access console from Python:
```python
def on_console_message(self, level, message, line, source):
    print(f"JS: {message} (line {line})")

self.page().javaScriptConsoleMessage = on_console_message
```

### Developer Tools
Enable debugging (development only):
```python
from qtpy.QtWebEngineWidgets import QWebEngineSettings

settings = self.page().settings()
settings.setAttribute(
    QWebEngineSettings.DeveloperExtrasEnabled,
    True
)
```

## Example: Simple Graph View

```python
from qtpy.QtWebEngineWidgets import QWebEngineView
from pathlib import Path
import json

class GraphView(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Load template
        template = Path(__file__).parent / "graph.html"
        self.setUrl(QUrl.fromLocalFile(str(template)))
        
    def display_graph(self, nodes, edges):
        """Send graph data to JavaScript."""
        data = {
            "nodes": nodes,
            "edges": edges
        }
        js = f"renderGraph({json.dumps(data)});"
        self.page().runJavaScript(js)
```

## Security Considerations

- **Validate external content** - Don't load untrusted URLs
- **Sanitize data** - Escape user input before sending to JS
- **Content Security Policy** - Restrict resource loading
- **HTTPS for external** - Use secure connections
- **Isolate sensitive data** - Don't expose secrets to JS
