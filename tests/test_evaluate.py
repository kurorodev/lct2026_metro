import unittest
from metro_guard.evaluate import evaluate


class EvaluationTests(unittest.TestCase):
    def test_no_labels_is_not_perfect_score(self):
        with self.assertRaises(ValueError): evaluate([],[])

    def test_confusion_and_unknown_miss(self):
        predictions=[{'frame_index':i,'status':s,'obstacle_detected':s=='obstacle','distance_m':10.} for i,s in enumerate(['obstacle','obstacle','unknown','no_obstacle_observed'])]
        labels=[{'frame_index':i,'obstacle_present':t} for i,t in enumerate([True,False,True,False])]
        result=evaluate(predictions,labels)
        self.assertEqual([result[k] for k in ('tp','fp','tn','fn')],[1,1,1,1])
        self.assertEqual(result['recall'],.5)

    def test_labels_from_other_bag_are_rejected(self):
        predictions=[{'frame_index':0,'bag_timestamp':10.,'status':'unknown','obstacle_detected':False}]
        labels=[{'frame_index':0,'bag_timestamp':20.,'obstacle_present':True}]
        with self.assertRaises(ValueError): evaluate(predictions,labels)


if __name__=='__main__': unittest.main()
