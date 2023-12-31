package LeetCode75;

public class Compress {
    public int compress(char[] chars) {
        if (chars.length == 1) return 1;
        int curr = 0, length = 1;
        for (int i = 0; i < chars.length; i++, length = 1) {
            chars[curr++] = chars[i];
            while (i < chars.length - 1 && chars[i] == chars[i + 1]) {
                length++;
                i++;
            }

            if (length > 1) 
                for (char c : (""+length).toCharArray())
                    chars[curr++] = c;
        }

        return curr;
    }
}
