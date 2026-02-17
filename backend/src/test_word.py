input_string = "distilledandbottledby:abcdistilleryfrederick,mdabcsinglebarrelstraightryewhisky750ml45%alc/volbrandlabelabcstraightryewhiskygovernmentwarning:(1)accordingtothesurgeongeneral,womenshouldnotdrinkalcoholicbeveragesduringpregnancybecauseoftheriskofbirthdefects.(2)consumptionofalcoholicbeveragesimpairsyourabilitytodriveacaroroperatemachinery,andmaycausehealthproblems.23456\"789012backlabel"
test_words = ["Hi", "How", "Are", "you", "doing", "today?"]

for item in test_words:
    if (item.lower() in input_string):
        print(item.lower(), ": YES, IN STRING")
    else:
        print(item.lower(), ": NO, NOT IN STRING")