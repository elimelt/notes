TAXONOMY_JS = """
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
    
    // Create alphabet navigation and sections
    createAlphabetSections(items, container);
    
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
    // Handle alphabet sections filtering
    const sections = container.querySelectorAll('.alphabet-section');
    const alphabetNav = container.querySelector('.alphabet-nav');
    
    if (!sections.length) return;
    
    let anyVisible = false;
    
    sections.forEach(section => {
        const letter = section.querySelector('h2').textContent;
        const listItems = section.querySelectorAll('.taxonomy-list li');
        let sectionVisible = false;
        
        listItems.forEach(item => {
            const link = item.querySelector('a');
            const itemText = link.textContent.toLowerCase();
            
            if (itemText.includes(query)) {
                item.style.display = '';
                sectionVisible = true;
                anyVisible = true;
            } else {
                item.style.display = 'none';
            }
        });
        
        section.style.display = sectionVisible ? '' : 'none';
        
        // Update alphabet nav
        if (alphabetNav) {
            const alphabetLink = alphabetNav.querySelector(`a[href="#letter-${letter}"]`);
            if (alphabetLink) {
                if (sectionVisible) {
                    alphabetLink.classList.remove('empty');
                } else {
                    alphabetLink.classList.add('empty');
                }
            }
        }
    });
    
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
    
    // For categories, also filter the category cards if present
    if (isCategories) {
        const categoryCards = container.querySelectorAll('.category-card');
        categoryCards.forEach(card => {
            const categoryName = card.querySelector('h3').textContent.toLowerCase();
            if (categoryName.includes(query)) {
                card.style.display = '';
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
                } else {
                    tag.style.display = 'none';
                }
            });
        }
    }
}

function createAlphabetSections(items, container) {
    // Group items by first letter
    const groupedItems = {};
    const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
    
    alphabet.forEach(letter => {
        groupedItems[letter] = [];
    });
    
    // Add numeric and other categories
    groupedItems['0-9'] = [];
    groupedItems['#'] = [];
    
    items.forEach(item => {
        const firstChar = item.name.charAt(0).toUpperCase();
        if (alphabet.includes(firstChar)) {
            groupedItems[firstChar].push(item);
        } else if (/[0-9]/.test(firstChar)) {
            groupedItems['0-9'].push(item);
        } else {
            groupedItems['#'].push(item);
        }
    });
    
    // Create alphabet navigation
    const nav = document.createElement('div');
    nav.className = 'alphabet-nav';
    
    const allLetters = ['0-9', '#', ...alphabet];
    
    allLetters.forEach(letter => {
        const hasItems = groupedItems[letter].length > 0;
        
        const link = document.createElement('a');
        link.href = `#letter-${letter}`;
        link.textContent = letter;
        
        if (!hasItems) {
            link.className = 'empty';
            link.style.pointerEvents = 'none';
        }
        
        nav.appendChild(link);
    });
    
    container.appendChild(nav);
    
    // Create alphabet sections
    allLetters.forEach(letter => {
        const items = groupedItems[letter];
        if (items.length === 0) return;
        
        const section = document.createElement('div');
        section.className = 'alphabet-section';
        section.id = `letter-${letter}`;
        
        const heading = document.createElement('h2');
        heading.textContent = letter;
        section.appendChild(heading);
        
        const list = document.createElement('ul');
        list.className = 'taxonomy-list';
        
        items.forEach(item => {
            const li = document.createElement('li');
            
            const link = document.createElement('a');
            link.href = item.url;
            link.textContent = item.name;
            
            const count = document.createElement('span');
            count.className = 'count';
            count.textContent = item.count;
            
            li.appendChild(link);
            li.appendChild(count);
            list.appendChild(li);
        });
        
        section.appendChild(list);
        container.appendChild(section);
    });
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
        
        // Calculate size class based on frequency
        let sizeClass = 'tag-md';
        if (maxCount > minCount) {
            const ratio = (item.count - minCount) / (maxCount - minCount);
            if (ratio < 0.2) sizeClass = 'tag-xs';
            else if (ratio < 0.4) sizeClass = 'tag-sm';
            else if (ratio < 0.6) sizeClass = 'tag-md';
            else if (ratio < 0.8) sizeClass = 'tag-lg';
            else sizeClass = 'tag-xl';
        }
        
        link.className = sizeClass;
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
        count.innerHTML = `<span class="page-count">${item.count}</span> pages in this category`;
        
        const viewAll = document.createElement('a');
        viewAll.className = 'view-all';
        viewAll.href = item.url;
        viewAll.textContent = 'View all →';
        
        card.appendChild(heading);
        card.appendChild(count);
        card.appendChild(viewAll);
        
        cardsContainer.appendChild(card);
    });
    
    return cardsContainer;
}
"""
