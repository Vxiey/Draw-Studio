import unittest
from types import SimpleNamespace
from BrowserOneClick import choose_unique_candidate,candidate_score

class BrowserOneClickTests(unittest.TestCase):
    def c(self,conf=.9,count=18,canvas=True,area=1000000):
        return SimpleNamespace(confidence=conf,palette_count=count,canvas_box=(1,2,3,4) if canvas else None,area=area)
    def test_unique_high_confidence_candidate_wins(self):
        a=self.c(.93,72,True);b=self.c(.72,18,True)
        self.assertIs(choose_unique_candidate([b,a]),a)
    def test_ambiguous_candidates_fail_closed(self):
        with self.assertRaises(ValueError):choose_unique_candidate([self.c(.90,18),self.c(.89,18)])
    def test_low_confidence_fails_closed(self):
        with self.assertRaises(ValueError):choose_unique_candidate([self.c(.55,72)])
    def test_score_rewards_verified_palette_and_canvas(self):
        self.assertGreater(candidate_score(self.c(.8,72,True)),candidate_score(self.c(.8,6,False)))

if __name__=='__main__':unittest.main()
