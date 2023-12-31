package LeetCode75;

/* https://leetcode.com/problems/implement-trie-prefix-tree */

import java.util.HashMap;
import java.util.Map;

class Trie {
    private TrieNode root;

    public Trie() {
        this.root = new TrieNode(null, false);
    }
    
    public void insert(String word) {
        if (word == "") {
            this.root.contained = true;
            return;
        }

        TrieNode currNode = root;
        char[] chars = word.toCharArray();
        int i = 0;
        
        while (i < chars.length && currNode.pointers.containsKey(chars[i]))
            currNode = currNode.pointers.get(chars[i++]);

        while (i < chars.length) {
            currNode.pointers.put(chars[i], new TrieNode(chars[i], false));
            currNode = currNode.pointers.get(chars[i++]);
        }

        currNode.contained = true;

    }
    
    public boolean search(String word) {
        char[] chars = word.toCharArray();
        TrieNode currNode = root;
        int i = 0;

        while (i < chars.length && currNode.pointers.containsKey(chars[i]))
            currNode = currNode.pointers.get(chars[i++]);
        
        return i == chars.length && currNode.contained;
    }
    
    public boolean startsWith(String prefix) {
        char[] chars = prefix.toCharArray();
        TrieNode currNode = root;
        int i = 0;
        while (i < chars.length && currNode.pointers.containsKey(chars[i]))
            currNode = currNode.pointers.get(chars[i++]);

        return i == chars.length;
    }

    @Override
    public String toString() {
        return this.root.pointers.toString();
    }

    private class TrieNode {
        public Map<Character, TrieNode> pointers;
        public Character data;
        public boolean contained;

        public TrieNode(Character data, boolean contained) {
            this.data = data;
            this.contained = contained;
            this.pointers = new HashMap<>();
        }

        @Override
        public String toString() {
            return this.data + ": " + contained;
        }
    }
}
