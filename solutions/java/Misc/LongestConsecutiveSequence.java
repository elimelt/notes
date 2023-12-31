package Misc;
import java.util.HashSet;
import java.util.Set;

public class LongestConsecutiveSequence {
    public int longestConsecutive(int[] nums) {
        if (nums.length <= 1)
            return nums.length;
        Set<Integer> set = new HashSet<>();
        Set<Integer> visited = new HashSet<>();

        for (int n : nums) set.add(n);

        int maxStreak = 0, currStreak = 0;
        for (int n : nums) {
            
            if (visited.contains(n))
                continue; 
                
            currStreak = 1;    
            int curr = n;

            visited.add(curr);

            while (set.contains(++curr)) {
                currStreak++;
                visited.add(curr);
            }

            curr = n;

            while (set.contains(--curr)) {
                currStreak++;
                visited.add(curr);
            }
            
            maxStreak = Math.max(maxStreak, currStreak);
        }

        return maxStreak;
    }
}
