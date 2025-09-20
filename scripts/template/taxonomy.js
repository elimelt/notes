// Taxonomy pages enhancement - JavaScript to be included at the bottom of your template

document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a taxonomy page
    const isCategoriesPage = document.title.includes('Categories');
    const isTagsPage = document.title.includes('Tags');
    
    if (isCategoriesPage || isTagsPage) {
        enhanceTaxonomyPage(isCategoriesPage);
    }
});

function enhanceTaxonomyPage(isCategories) {
    const pageType = isCategories ? 'categories' : 'tags';
    const contentDiv = document.querySelector('.content');
    
    if (!contentDiv) return;
    
    // Get the original list
    const originalList = contentDiv.querySelector('ul');
    if (!originalList) return;
    
    // Extract items from the original list
    const items = Array.from(originalList.querySelectorAll('li')).map(li => {
        const link = li.querySelector('a');
        const text = li.textContent;
        const count = text.match(/\((\d+) pages\)/);
        
        return {
            name: link.textContent,
            url: link.getAttribute('href'),
            count: count ? parseInt(count[1]) : 0
        };
    });
    
    // Sort items alphabetically
    items.sort((a, b) => a.name.localeCompare(b.name));
    
    // Create new enhanced container
    const container = document.createElement('div');
    container.className = 'taxonomy-container';
    
    // Add search functionality
    const searchBox = createSearchBox(items, container, isCategories);
    container.appendChild(searchBox);
    
    if (isCategories) {
        // For categories, create card view
        const categoryCards = createCategoryCards(items);
        container.appendChild(categoryCards);
    } else {
        // For tags, add tag cloud
        const tagCloud = createTagCloud(items);
        container.appendChild(tagCloud);
    }
    
    // No more alphabet navigation - just show the tag cloud or category cards
    
    // Replace the original content with our enhanced version
    contentDiv.innerHTML = '';
    contentDiv.appendChild(container);
}

function createSearchBox(items, container, isCategories) {
    const searchContainer = document.createElement('div');
    searchContainer.className = 'taxonomy-search';
    
    const searchLabel = document.createElement('label');
    searchLabel.setAttribute('for', 'taxonomy-search-input');
    searchLabel.textContent = `Search ${isCategories ? 'categories' : 'tags'}:`;
    
    const inputContainer = document.createElement('div');
    inputContainer.className = 'search-container';
    
    const input = document.createElement('input');
    input.id = 'taxonomy-search-input';
    input.type = 'text';
    input.placeholder = `Filter ${isCategories ? 'categories' : 'tags'}...`;
    
    const searchIcon = document.createElement('span');
    searchIcon.className = 'search-icon';
    searchIcon.innerHTML = '🔍';
    
    inputContainer.appendChild(input);
    inputContainer.appendChild(searchIcon);
    
    searchContainer.appendChild(searchLabel);
    searchContainer.appendChild(inputContainer);
    
    // Add event listener for filtering
    input.addEventListener('input', function() {
        const query = this.value.toLowerCase();
        filterItems(query, container, items, isCategories);
    });
    
    return searchContainer;
}

function filterItems(query, container, items, isCategories) {
    let anyVisible = false;
    
    // For categories, filter the category cards
    if (isCategories) {
        const categoryCards = container.querySelectorAll('.category-card');
        categoryCards.forEach(card => {
            const categoryName = card.querySelector('h3').textContent.toLowerCase();
            if (categoryName.includes(query)) {
                card.style.display = '';
                anyVisible = true;
            } else {
                card.style.display = 'none';
            }
        });
    }
    
    // For tags, filter the tag cloud
    if (!isCategories) {
        const tagCloud = container.querySelector('.tag-cloud');
        if (tagCloud) {
            const tags = tagCloud.querySelectorAll('a');
            tags.forEach(tag => {
                const tagName = tag.textContent.split(' ')[0].toLowerCase();
                if (tagName.includes(query)) {
                    tag.style.display = '';
                    anyVisible = true;
                } else {
                    tag.style.display = 'none';
                }
            });
        }
    }
    
    // Show no results message if needed
    let noResultsMsg = container.querySelector('.no-results');
    
    if (!anyVisible) {
        if (!noResultsMsg) {
            noResultsMsg = document.createElement('div');
            noResultsMsg.className = 'no-results';
            noResultsMsg.textContent = 'No matching results found.';
            container.appendChild(noResultsMsg);
        }
    } else if (noResultsMsg) {
        noResultsMsg.remove();
    }
}


function createTagCloud(items) {
    const cloudContainer = document.createElement('div');
    cloudContainer.className = 'tag-cloud';
    
    // Sort by frequency
    const sortedItems = [...items].sort((a, b) => b.count - a.count);
    
    // Find the min and max counts
    const counts = items.map(item => item.count);
    const maxCount = Math.max(...counts);
    const minCount = Math.min(...counts);
    
    // Create size classes
    sortedItems.forEach(item => {
        const link = document.createElement('a');
        link.href = item.url;
        
        // Calculate font size based on frequency
        const maxSize = 30;
        const minSize = 10;
        let size = minSize;
        if (maxCount > minCount) {
            const ratio = (item.count - minCount) / (maxCount - minCount);
            size = Math.round(ratio * (maxSize - minSize)) + minSize;
        }
        
        link.style.fontSize = size + '%';
        link.textContent = `${item.name} (${item.count})`;
        
        cloudContainer.appendChild(link);
    });
    
    return cloudContainer;
}

function createCategoryCards(items) {
    const cardsContainer = document.createElement('div');
    cardsContainer.className = 'category-cards';
    
    // Sort by number of pages (descending)
    const sortedItems = [...items].sort((a, b) => b.count - a.count);
    
    sortedItems.forEach(item => {
        const card = document.createElement('div');
        card.className = 'category-card';
        
        const heading = document.createElement('h3');
        heading.textContent = item.name;
        
        const count = document.createElement('p');
        count.innerHTML = `<span class="page-count">
          <a href="${item.url}">
          ${item.count}
          </a>
        </span> pages in this category`;
        
        card.appendChild(heading);
        card.appendChild(count);
        
        cardsContainer.appendChild(card);
    });
    
    return cardsContainer;
}
