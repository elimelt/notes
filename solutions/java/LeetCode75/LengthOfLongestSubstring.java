package LeetCode75;

/* https://leetcode.com/problems/longest-substring-without-repeating-characters */

import java.util.HashSet;
import java.util.Set;

public class LengthOfLongestSubstring {
    public int lengthOfLongestSubstring(String s) {
        int lo = 0, hi = 0, max = 0;
        Set<Character> set = new HashSet<>();

        while (hi < s.length()) {
            char curr = s.charAt(hi);

            if (!set.contains(curr))
                set.add(s.charAt(hi++));
            else 
                set.remove(s.charAt(lo++));

            max = Math.max(max, hi - lo);
        }

        return max;
    }
}
