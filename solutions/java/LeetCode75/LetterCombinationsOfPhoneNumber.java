package LeetCode75;
import java.util.*;

public class LetterCombinationsOfPhoneNumber {
    List<String> list = new ArrayList<>();
    Map<Integer, char[]> map = new HashMap<>();
    public List<String> letterCombinations(String digits) {
        if (digits.length() == 0) return this.list;
        for (int i = 2; i < 7; i++) {
            map.put(i, new char[3]);
            for (int j = 0; j < 3; j++) 
                map.get(i)[j] = ((char) ((int) 'a' + (i - 2)*3 + j));
        }
        map.put(7, new char[]{'p', 'q', 'r', 's'});
        map.put(8, new char[]{'t', 'u', 'v'});
        map.put(9, new char[]{'w', 'x', 'y', 'z'});
        StringBuilder sb =  new StringBuilder(digits);
        fillList(digits, sb, 0);
        return this.list;
    }

    private void fillList(String digits, StringBuilder curr, int i) {
        if (i == digits.length()) this.list.add(curr.toString());
        else {
            for (char c : this.map.get(Integer.parseInt(""+digits.charAt(i)))) {
                curr.setCharAt(i, c);
                fillList(digits, curr, i + 1);
            }   
        }
    }
}
