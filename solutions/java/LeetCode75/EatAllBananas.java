package LeetCode75;

/* https://leetcode.com/problems/koko-eating-bananas */

public class EatAllBananas {
    public int minEatingSpeed(int[] piles, int h) {
        int maxPileSize = piles[0];
        for (int n : piles) maxPileSize = Math.max(n, maxPileSize);
        if (piles.length == h) return maxPileSize;
        return findOptimalSpeed(0, maxPileSize, piles, h);

    }

    private int findOptimalSpeed(int lowSpeed, int highSpeed, int[] piles, int h) {
        int midSpeed = lowSpeed + (highSpeed - lowSpeed)/2;
        if (highSpeed == midSpeed) return highSpeed;

        int time = 0;
        for (int pile : piles) {
            // find time to eat all 
            time += Math.ceil((double) pile/midSpeed);
            // if run out of time
            if (time > h) break;
                
        }

        return time > h 
            ? findOptimalSpeed(midSpeed + 1, highSpeed, piles, h)
            : findOptimalSpeed(lowSpeed, midSpeed, piles, h);
    }
}
