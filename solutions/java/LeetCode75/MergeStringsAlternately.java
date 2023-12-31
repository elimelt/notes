package LeetCode75;

class MergeStringsAlternately {
    public String mergeAlternately(String word1, String word2) {
        StringBuilder sb = new StringBuilder();
        int minLength = Math.min(word1.length(),  word2.length());
        
        for (int i = 0; i < minLength; i++)
            sb.append(word1.charAt(i) + "" + word2.charAt(i));

        if (minLength == word1.length()) 
            sb.append(word2.substring(minLength, word2.length()));
        else 
            sb.append(word1.substring(minLength, word1.length()));
        
        return sb.toString();
    }
}