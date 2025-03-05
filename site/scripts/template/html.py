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
    {% include 'styles' %}
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
<div class="landing-stats">
    <div class="stat-item">
        <span class="stat-value">{{ stats.notes }}</span>
        <span class="stat-label">Notes</span>
    </div>
    <div class="stat-item">
        <span class="stat-value">{{ stats.categories }}</span>
        <span class="stat-label">Categories</span>
    </div>
    <div class="stat-item">
        <span class="stat-value">{{ stats.tags }}</span>
        <span class="stat-label">Tags</span>
    </div>
</div>
<div class="landing-grid">
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
    <div class="categories-section">
        <h2>Categories</h2>
        <ul class="categories-list">
        {% for category in categories %}
            <li>
                <a href="{{ category.url }}">{{ category.name }}</a>
                <span class="count">({{ category.count }})</span>
            </li>
        {% endfor %}
        </ul>
    </div>
    <div class="tags-section">
        <h2>Featured Tags</h2>
        <div class="tags-cloud">
        {% for tag in popular_tags %}
            <a href="{{ tag.url }}" class="tag-{{ tag.size_class }}">
                {{ tag.name }} <span>({{ tag.count }})</span>
            </a>
        {% endfor %}
        </div>
    </div>
</div>
"""
