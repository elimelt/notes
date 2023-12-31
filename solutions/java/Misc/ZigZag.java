package Misc;

public class ZigZag {
    public String convert(String s, int numRows) {

        if (numRows == 1) 
            return s;

        char[][] grid = new char[numRows][s.length()];

        int col = 0;
        int numPlaced = 0;
        while (numPlaced < s.length()) {
            for (int row = 0; row < numRows && numPlaced < s.length(); row++) 
                grid[row][col] = s.charAt(numPlaced++);

            col++;

            for (int i = 0, row = numRows - 2; i < numRows - 2 && numPlaced < s.length(); i++)
                grid[row--][col++] = s.charAt(numPlaced++);
        }

        StringBuilder sb = new StringBuilder();

        for (char[] r : grid) 
            for (char c : r)
                if (c != 0) sb.append(c);
        
        return sb.toString();
    }
}
