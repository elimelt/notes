package Misc;

import java.util.HashMap;
import java.util.Map;

public class IsValidAnagram {
    public boolean isAnagram(String s, String t) {
        if (s.length() != t.length())
            return false;
        Map<Character, Integer> map = new HashMap<>();

        for (int i = 0; i < s.length(); i++)
            map.put(s.charAt(i), map.getOrDefault(s.charAt(i), 0) + 1);

        for (int i = 0; i < s.length(); i++)
            map.put(t.charAt(i), map.getOrDefault(t.charAt(i), 0) - 1);

        for (int i = 0; i < s.length(); i++)
            if (map.get(s.charAt(i)) != 0)
                return false;
        
        for (int i = 0; i < s.length(); i++)
            if (map.get(t.charAt(i)) != 0)
                return false;

        return true;
    }
}
