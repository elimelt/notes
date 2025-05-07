BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}{% if title %} | {% endif %}Elijah's Notes</title>

    <!-- SEO Meta Tags -->
    <meta name="description" content="{{ meta_description }}">
    <meta name="author" content="Elijah Melton">
    <meta name="robots" content="index, follow">
    <meta name="generator" content="Custom Static Site Generator">
    <link rel="canonical" href="{{ canonical_url }}">

    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="article">
    <meta property="og:title" content="{{ title }}">
    <meta property="og:description" content="{{ meta_description }}">
    <meta property="og:url" content="{{ canonical_url }}">

    <!-- Twitter -->
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{{ title }}">
    <meta name="twitter:description" content="{{ meta_description }}">

    {% if tags %}
    <meta name="keywords" content="{{ tags|join(',') }}">
    {% endif %}

    <!-- Schema.org JSON-LD -->
    <script type="application/ld+json">
    {{ schema_json|safe }}
    </script>

    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.7.1/katex.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.7.1/katex.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.7.1/contrib/auto-render.min.js"></script>

    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/default.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <!-- and it's easy to individually load additional languages -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/verilog.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/python.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/java.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/cpp.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/c.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.css"></script>

    <link rel="stylesheet" href=/css/styles.css>

    <!-- Configure KaTeX auto-render -->
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            renderMathInElement(document.body, {
                delimiters: [
                    {left: "$$", right: "$$", display: true},
                    {left: "\\[", right: "\\]", display: true},
                    {left: "$", right: "$", display: false},
                ],
                preProcess: (math) => {
                    console.log("Pre-processing: " + math);
                    math = math.split("\\n").map((line) => {
                        if (line.endsWith("\\\\")) {
                            return line + "\\\\";
                        }
                        return line;
                    }).join("\\n");
                    return math;
                },
                throwOnError: false
            });
        });
    </script>
    <!-- Configure Highlight.js -->
    <script>hljs.highlightAll();</script>
</head>
<body>
    <header>
        <nav role="navigation" aria-label="Main navigation">
            {{ navigation|safe }}
        </nav>
        <div class="breadcrumbs" role="navigation" aria-label="Breadcrumb">
            {{ breadcrumbs|safe }}
        </div>
    </header>
    <main role="main">
        <article>
            {% if title %}
            <h1>{{ title }}</h1>
            {% endif %}
            <div class="meta">
                <time datetime="{{ modified_date.isoformat() }}">
                    Last modified: {{ modified_date.strftime('%Y-%m-%d') }}
                </time>
                {% if category %}
                <span>Category: <a href="/categories/{{ category|lower|urlencode }}.html">{{ category }}</a></span>
                <span><a id="parent-link" href="index.html">..</a></span>
                {% endif %}
            </div>
            <div class={{ css_selector }}>
                {{ content|safe }}
            </div>
            {% if tags %}
            <div class="tags">
                Tags:
                {% for tag in tags|sort %}
                <a href="/tags/{{ tag|lower|urlencode }}.html">{{ tag }}</a>
                {% endfor %}
            </div>
            {% endif %}
        </article>
    </main>
    <footer role="contentinfo">
        <p>{{ current_year }}, authored by Elijah Melton.</p>
    </footer>
</body>
</html>
"""

INDEX_TEMPLATE = """
<!-- Main container for the grid layout -->
<div class="landing-grid">
    <!-- Stats section at the top -->
    <div class="stats-section">
        <div class="stat-item">
            <div class="stat-number">156</div>
            <div class="stat-label">Notes</div>
        </div>
        <div class="stat-item">
            <div class="stat-number">21</div>
            <div class="stat-label">Categories</div>
        </div>
        <div class="stat-item">
            <div class="stat-number">612</div>
            <div class="stat-label">Tags</div>
        </div>
    </div>

    <div class="main-content-wrapper">
        <!-- Main content area -->
        <!-- Sidebar area -->
        <div class="content-area">
            <!-- Recent posts section -->
            <div class="recent-section">
                <h2>Recent</h2>
                <ul class="recent-posts">
                    {% for page in recent_pages %}
                    <li>
                        <a href="{{ page.url }}">{{ page.title }}</a>
                        <span class="date">{{ page.date }}</span>
                        {% if page.category %}
                        <span class="category">{{ page.category }}</span>
                        {% endif %}
                    </li>
                    {% endfor %}
                </ul>
            </div>

            <!-- Tags section -->
            <div class="tags-section">
                <h2>Featured Tags</h2>
                <div class="tags-cloud">
                    {% for tag in popular_tags %}
                    <a href="{{ tag.url }}" class="tag-{{ tag.size_class }}">
                        {{ tag.name }} <span class="count">({{ tag.count }})</span>
                    </a>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>
</div>
"""
