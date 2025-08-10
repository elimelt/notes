package LeetCode75;

public class KthLargestElement {
    public int findKthLargest(int[] nums, int k) {
        int[] buckets = new int[20001];
        for (int n : nums)
            buckets[n + 10000]++;

        for (int i = buckets.length - 1; i >= 0; i--) {
            if (buckets[i] > 0)
                k -= buckets[i];
            if (k <= 0)
                return i - 10000;
        }
        return -1;
    }
}
