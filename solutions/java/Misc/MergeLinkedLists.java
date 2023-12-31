package Misc;

/* https://leetcode.com/problems/merge-in-between-linked-lists */

import Misc.ReorderList.ListNode;

public class MergeLinkedLists {
    public ListNode mergeInBetween(ListNode list1, int a, int b, ListNode list2) {
        ListNode lo = list1, hi = list1;

        for (int i = 0; i < b - a; i++)
            hi = hi.next;

        for (int i = 0; i < a - 1; i++) {
            hi = hi.next;
            lo = lo.next;
        }

        hi = hi.next;
        lo.next = list2;

        while (lo.next != null)
            lo = lo.next;
        
        lo.next = hi.next;

        return list1;
    }
}
