package LeetCode75;
import java.util.HashSet;
import java.util.Set;

public class ReverseVowels {
    public String reverseVowels(String s) {
        if (s.length() == 1) return s;

        Set<Character> v = new HashSet<>();
        v.add('a'); v.add('e'); v.add('i'); v.add('o'); v.add('u');
        v.add('A'); v.add('E'); v.add('I'); v.add('O'); v.add('U');

        StringBuilder sb = new StringBuilder();
        int left = 0, right = s.length() - 1;
        char[] arr = s.toCharArray();
        
        while (left < right) {
            if (!v.contains(arr[left])) 
                left++;
            else if (!v.contains(arr[right])) 
                right--;
            else {
                arr = swap(arr, left, right);
                left++; 
                right--;
            }
        }

        for (char c : arr) sb.append(c);
        return sb.toString();
    }

    private char[] swap(char[] s, int a, int b) {
        char temp = s[a];
        s[a] = s[b];
        s[b] = temp;
        return s;
    }
}
