package Misc;

import java.util.Arrays;
import java.util.HashMap;

/* https://leetcode.com/problems/contains-duplicate */

/* https://leetcode.com/problems/contains-duplicate-ii */

/* https://leetcode.com/problems/contains-duplicate-iii */

import java.util.HashSet;
import java.util.Map;
import java.util.Set;

public class ContainsDuplicate {
    public boolean containsDuplicate(int[] nums) {
        Set<Integer> set = new HashSet<>();
        for (int n : nums) if (!set.add(n)) return true;
        return false;
    }


    public boolean containsNearbyDuplicate(int[] nums, int k) {
        Map<Integer, Integer> map = new HashMap<>();

        for (int i = 0; i < nums.length; i++) {
            if (map.containsKey(nums[i]) && Math.abs(i - map.get(nums[i])) <= k)
                return true;
            map.put(nums[i], i);
        }

        return false;
    }

    public boolean containsNearbyAlmostDuplicate(int[] nums, int indexDiff, int valueDiff) {
        Pair[] pairs = new Pair[nums.length];
        for (int i = 0; i < nums.length; i++)
            pairs[i] = new Pair(i, nums[i]);
        
        Arrays.sort(pairs, (a, b) -> (int) a.getValue() - (int) b.getValue());
        Pair prev, curr;

        for (int i = 0; i < nums.length; i++) {
            int hi = i + 1;

            while (hi < nums.length) {
                if (Math.abs((int) pairs[i].getValue() - (int) pairs[hi].getValue()) > valueDiff)
                    break;
                if (Math.abs((int) pairs[i].getKey() -(int) pairs[hi++].getKey()) > indexDiff)
                    continue;
                
                return true;
            }

        }

        return false;

    }

    class Pair {
        private int k, v;
        public Pair(int key, int val) { k = key; v = val;}
        public int getKey() { return k; }
        public int getValue() { return v; }
    }
}
