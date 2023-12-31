package LeetCode75;

public class CanPlaceFlowers {
    public boolean canPlaceFlowers(int[] flowerbed, int n) {
        if (n <= 0)
            return true;
        if (n > flowerbed.length)
            return false;
        if (n == 1 && flowerbed.length == 1)
            return flowerbed[0] == 0;

        int count = 0;
        if (flowerbed[0] == 0 && flowerbed[1] == 0)
            flowerbed[count++] = 1;

        for (int curr = 2; curr < flowerbed.length; curr++) {
            if (flowerbed[curr] == 0 && flowerbed[curr - 1] == 0 && flowerbed[curr - 2] == 0) {
                flowerbed[curr - 1] = 1;
                count++;
            }
        }

        if (flowerbed[flowerbed.length - 1] == 0 && flowerbed[flowerbed.length - 2] == 0)
            count++;
        return count >= n;
    }
}
