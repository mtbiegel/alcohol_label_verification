# ProofCheck™ - My Thoughts During This Project

**Author:** Mark Biegel  
**Project/Description:** AI-Powered Alcohol Label Verification Tool  
**Date:** February 20th, 2026 (Developed in a single week)

For more/other info, read `README.md` and `PROJECT_REFLECTION.md`

## my thoughts

So, my thought process went in many different directions for this task.

Initially, the approaches I considered for classification were: local CPU-only, local GPU, API call to an existing LLM service, or a hybrid approach between CPU and LLM API calls. When it comes to software, I am very much someone who believes in being as self-sustaining and independent as possible, without relying on other companies or services.

That being said, this is a take-home assignment with the sole intent of being a prototype to inform officials of what they would need in order to make an AI-powered alcohol label verifier application a reality in the government. For this prototype, to achieve the most efficiency and accuracy, the need to use an external vendor—specifically OpenAI—ended up being at the top of my list of solutions. But let me explain my thought process first.

I went through many stages of decision-making while developing this app. I first started with local CPU-based OCR and classification. This approach was decent; however, it did not provide accuracy anywhere near the level needed while meeting the criterion of being under 5 seconds per run. Therefore, it would not help an official make a procurement decision about implementing a label verifier, so I moved on to GPU-based approaches.

A GPU application would have opened the door to using other open-source models for OCR and classification. My issue here was that I unfortunately did not have access to the necessary hardware during development, which would have severely limited my ability to develop the app. Additionally, this approach would have been ambitious and could have resulted in unfinished features. I therefore determined that this was not the right path.

This left me with finding a way to use another platform service, like OpenAI or Claude, to make API calls for OCR and classification. While the criteria stated that some vendor features could be unusable due to network restrictions, using OpenAI was feasible because the prompt stated access to Microsoft Azure, and openAI API endpoints have been available on Azure as of early 2026 at FedRAMP High, meaning the openAI API calls will work. So, given the constraints described and the solid possibility of accessing OpenAI API endpoints through Azure (and after three long days struggling with my local classifier), I concluded that API calls are the best approach for this assessment given the time and resource constraints.

I considered a hybrid approach, where a local CPU-based classifier would attempt classification first, and if it failed, the OpenAI API would make the final determination. I found this improved accuracy by a small factor compared to using OpenAI alone, so I left it in even if it wasn't as useful as I wanted it to be.

Now, I know using an API call to an external LLM provider seems like a cop-out, and don’t get me wrong—my first thought was to do everything locally, but considering the level of effort needed to create a well-crafted, completed webapp in the timeline I was given, it was not in the cards for this project. While I am capable of developing that kind of software, I unfortunately did not have the time or computing power to run models of that scale locally on my personal machine during development. I chose to focus on having a core application that worked well with clean code rather than pursuing an ambitious approach that could have led to incomplete features.

Looking forward to future improvements, with more access to people who understand government system limitations, I would be able to more effectively determine the best approach. Ideally, I would want to run this locally using a few GPUs in a server or even on a single desktop that could run pre-trained (or trainable) open-source models.

I will admit this is my first take-home assessment for a job interview, and whether the goal was to create a fully working application with some drawbacks or to demonstrate engineering decisions, I want to clarify that my choice to use the OpenAI API API and prompt engineering was NOT due to laziness. I spent many nights (Saturday through Tuesday) trying to develop an accurate local CPU-based application that I knew could scale to GPU if I had access.

That being said, I really enjoyed this take-home project. Although it was challenging at times, it pushed me to do some deep critical thinking that my current job hasn’t required of me in a long time 😂. This is the type of work I would enjoy doing on a day-to-day basis and wish my current job had similar tasks.