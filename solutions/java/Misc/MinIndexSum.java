package Misc;

import java.util.HashMap;
import java.util.Map;

public class MinIndexSum {
    public String[] findRestaurant(String[] list1, String[] list2) {
        Map<String, Integer> indexMap = new HashMap<>();
        Map<String, Integer> sumMap = new HashMap<>();

        for (int i = 0; i < list1.length; i++)
            indexMap.put(list1[i], i);

        for (int i = 0; i < list2.length; i++)
            if (indexMap.containsKey(list2[i]))
                sumMap.put(list2[i], i + indexMap.get(list2[i]));

        int min = Integer.MAX_VALUE, len = 1;
        for (String s : sumMap.keySet()) {
            int c = sumMap.get(s);
            if (min > c) {
                min = c;
                len = 1;
            } else if (min == c)
                len++;
        }

        String[] ans = new String[len];
        if (len == 0)
            return ans;
        int i = 0;
        for (String s : sumMap.keySet())
            if (min == sumMap.get(s))
                ans[i++] = s;
        return ans;

    }
}
