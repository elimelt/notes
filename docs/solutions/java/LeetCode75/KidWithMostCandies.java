package LeetCode75;

import java.util.ArrayList;
import java.util.List;

public class KidWithMostCandies {
    public List<Boolean> kidsWithCandies(int[] candies, int extraCandies) {
        List<Boolean> l = new ArrayList<>();
        int max = Integer.MIN_VALUE;
        for (int n : candies)
            max = Math.max(max, n);
        for (int n : candies)
            l.add(n + extraCandies >= max);
        return l;
    }
}
