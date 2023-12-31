package LeetCode75;

public class FindPeakElement {
    public int findPeakElement(int[] nums) {
        int start = 0, end = nums.length - 1, mid;

        while (start < end) {
            mid = start + (end - start - 1) / 2;
            if (nums[mid] < nums[mid + 1])
                start = mid + 1;
            else
                end = mid;
        }
        return start;
    }
}
