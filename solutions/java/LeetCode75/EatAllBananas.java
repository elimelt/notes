package LeetCode75;

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
            
            time += Math.ceil((double) pile/midSpeed);
            
            if (time > h) break;
                
        }

        return time > h 
            ? findOptimalSpeed(midSpeed + 1, highSpeed, piles, h)
            : findOptimalSpeed(lowSpeed, midSpeed, piles, h);
    }
}
