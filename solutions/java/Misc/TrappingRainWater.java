package Misc;

/* https://leetcode.com/problems/trapping-rain-water */

public class TrappingRainWater {
    public int trap(int[] height) {
        int[] rightMax = new int[height.length];
        int[] leftMax = new int[height.length];
        int rMax = 0, lMax = 0;

        for (int i = 0; i < height.length; i++) {
            rightMax[rightMax.length - i - 1] = rMax;
            leftMax[i] = lMax;
            rMax = Math.max(rMax, height[rightMax.length - i - 1]);
            lMax = Math.max(lMax, height[i]);
        }

        int water = 0;

        for (int i = 0; i < height.length; i++) {
            int waterHeight = Math.min(rightMax[i], leftMax[i]);
            if (waterHeight - height[i] > 0)
                water += waterHeight - height[i];
        }

        return water;

    }
}
