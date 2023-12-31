package LeetCode75;

/* https://leetcode.com/problems/n-th-tribonacci-number */

public class Tribonacci {
    public int tribonacci(int n) {
        if (n == 0 || n == 1) return n;
        if (n == 2) return 1;

        int a = 0, b = 1, c = 1, temp;
        for (int i = 0; i < n - 2; i++) {
            temp = c;
            c += a + b;
            a = b;
            b = temp;
        }

        return c;
    }
}
