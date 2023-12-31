package LeetCode75;
/* https://leetcode.com/problems/greatest-common-divisor-of-strings */

public class GCDOfStrings {
    // im just having fun here...never in a real codebase
    public String gcdOfStrings(String str1, String str2) {
        return (!(str1 + str2).equals(str2 + str1)) ?  "" : str1.substring(0, gcd(str1.length(), str2.length()));
    }

    private int gcd(int a, int b) {
        return (b == 0) ? a : gcd(b, a%b);
    }
}
