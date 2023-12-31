# https://leetcode.com/problems/longest-repeating-character-replacement/

class Solution:
    def characterReplacement(self, s: str, k: int) -> int:
        lo, hi, res = 0, 0, 0
        cMap = {}
        
        while (hi < len(s)):
            c = s[hi]
            cMap[c] = 1 if c not in cMap else cMap[c] + 1

            while (hi - lo + 1) - max(cMap.values()) > k:
                cMap[s[lo]] -= 1
                lo += 1 
        
            hi += 1
            res = max(res, hi - lo)

        return res