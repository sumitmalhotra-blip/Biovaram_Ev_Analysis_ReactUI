Dec 11, 2025

## Biovaram Weekly Customer Connect.  \- Transcript

### 00:43:56

   
**Sumit Malhotra:** and large particles are there and they can see the data visually. Then going forward the ultimate selection that we made above with the scatter plot we will be also showing these type of things. Now this is the basic understanding of the data that they want to see. Now apart from this they will be integrating AI to help scientists with this analysis with different scenarios and different type of things. So that will be proceeding further in by the next week right  
**Parvesh Reddy:** Yeah.  
**Sumit Malhotra:** Pravesh.  
**Parvesh Reddy:** So we will be configuring AWS today and then starting from tomorrow onwards we should be able to start uh integrating the  
**Sumit Malhotra:** Yeah.  
**Parvesh Reddy:** AI  
**Sumit Malhotra:** And similarly this type of structure is we implemented into nanoparticle tracking as well as per the nanoparticle tracking norms like the flow seytometry has some requirements. Similarly, the nanoparticle tracking has some requirements and we can just simply upload a file here any nanoparticle tracking file. Let's say we choose this file. It is in a text format. it will be also converted into packet all the columns because initially what happened was we don't have the uh perfect data or you can say the right data to calculate the data that we got was just on an experimental basis for us to understand how the data looks like and how the data  
   
 

### 00:45:20

   
**Sumit Malhotra:** works but till today we data which we can use to you can say articulate all the analysis at once we will be doing it separately for now but we will shown we will be getting some data from there and as well the high quality data that they run into their previous analysis into their laboratories. So we will be able to integrate that and do the combination of analysis that they expect. So this is in the talks with them. Now similarly when we upload the NTA data it will calculate some of the key metrices how many uh data is available into the NTA file. They based upon that it will create some size distribution graph concentration profiles and their views and we can also download their reports into their specific format whatever they want. If they want in PDF they can want they download in PDF if they want in packet or if they even want in CSV as well it will be converted into that and downloaded into their system. And apart from that there is one cross comparison tab where all the two files that we uploaded previously it will be automatically picking up those files.  
   
 

### 00:46:30

   
**Sumit Malhotra:** We can run the combine analysis here tab on both the files. So this is that functionality we implemented till now based upon the requirement that we get. Now similarly what we did is previously this is the streamllet UI as Praves was telling. So this is the streamllet UI that we had. Now the with the streaml UI we are getting two or three issues. One is the consistency issue like it will be losing it consist consistency of the page. If I am shifting to the different page sometime it will lose their data or it will not be able to retain that data. So what we did is we shifted to the react UI. So this is the new UI that we created into the last week. It is not completely completely connected yet with the back end. There are some things that are missing but major of the things already connected. So basically the new UI looks something like this now. So it will be able to much more give us a much more cleaner view of each and everything.  
   
 

### 00:47:30

   
**Sumit Malhotra:** It will be able to give uh you can say much more better understanding of data as well and mostly it will be less size of uh li you can say less in less taking size as per the streamllet UI so it will be much lightweighted as  
**BoardRoom\_FS Conf Room:** Okay,  
**Sumit Malhotra:** well  
**BoardRoom\_FS Conf Room:** sure. Thank you. Thank you. So, anything else you want to share, Sit?  
**Sumit Malhotra:** uh not at the moment. Uh basically this is what I had like me Mohit and the team done till yet. This is all the UI structure and the back end system that we created till now. And from further on we will be going ahead with the AI part. We will be setting up the AI systems. We will be training the model and integrating into the system to check the further functionalities.  
**Parvesh Reddy:** Yeah. So, Charmy, can you go into a little bit more detail about that that section like the AI section? What we're going to do, how we're going to do it.  
   
 

### 00:48:26

   
**Charmi Dholakia:** Yeah, sure. So, one second.  
**Sumit Malhotra:** If you need to share the screen, Char me, I can stop sharing.  
**Charmi Dholakia:** Huh? Yeah. No, no. So, it's okay. So, what we need to do is we'll be reading these insurance PDFs, plan documents, whatever client data is there. Then we will be uh generating whatever answers. So basically we need to decide what the user actually wants right. So we will generate all the correct answers the PDF. So we will be doing a process of rag which is retrieval augmented generation. We'll do agentic AI some kind of a query planner. So whatever the question is asked then the so rag basically is whatever data we give and whatever answer is what we need to get from the data. So that is kind of a chat thing and that we do so that we will be able to uh you know make use of AI and generative AI the LLMs will be used. So these all will be used in order to create that chat we will be feeding in our data into the knowledge base and based on rag pipeline we will be uh you know making the answers.  
   
 

### 00:49:45

   
**Charmi Dholakia:** So some kind of a correlation some kind of ambiguity detection. So any kind so these all things will process insights we'll be using LLMs also statistical modeling also but these things will be used in order to get those answers which the users will be asking us.  
**BoardRoom\_FS Conf Room:** Okay. Char, what kind of statistical modeling that you have? You're planning to use it.  
**Charmi Dholakia:** So statistical modeling some kind of uh binary classification like XG boost model or a random forest model that will say this is an ambiguous or a non-amb ambiguous kind of a uh scenario.  
**BoardRoom\_FS Conf Room:** Okay. And uh so currently you are planning to use uh uh cloud as the platform right?  
**Charmi Dholakia:** AWS as the platform and AWS has many uh models like Nova, Anthropic, uh there is Amazon itself has Titan embeddings. So these are there are different a lot of uh providers are there on Amazon on AWS that gives their LLM to AWS which we can get access to. So Titan uh anthropic anthropic claim cloud models are also there that also we can use.  
   
 

### 00:50:58

   
**Charmi Dholakia:** So yeah, uh there are a lot of options that we can select from on  
**BoardRoom\_FS Conf Room:** Okay.  
**Charmi Dholakia:** AWS.  
**BoardRoom\_FS Conf Room:** And uh at what stage you are going to decide on which one to use?  
**Charmi Dholakia:** It depends on how much are some models are costly models, some models are paid, some models are free versions. So what models we can uh do? So anthropic claude models are good models. there are certain models which are uh you know specifically designed for uh special business cases. So if we need that then that also we can go ahead and purchase that. So maybe that we can do it later. Right now we can continue with the anthropic models, claude  
**BoardRoom\_FS Conf Room:** Okay, fine.  
**Charmi Dholakia:** models.  
**BoardRoom\_FS Conf Room:** Yeah. Well, thank you. Thanks, Charm. And I'm just trying to understand this. Let me spend some more time with the team and then you know we will catch up again. Thanks for uh you know sharing the details uh at this stage.  
   
 

### 00:52:00

   
**Charmi Dholakia:** Yeah. Yeah.  
**BoardRoom\_FS Conf Room:** That's all from my side.  
**Charmi Dholakia:** Thank you.  
**BoardRoom\_FS Conf Room:** Yeah, I think you know you can stay online probably and Sumit can sign  
**Parvesh Reddy:** Yeah.  
**BoardRoom\_FS Conf Room:** off.  
**Sumit Malhotra:** Okay.  
**Parvesh Reddy:** Yeah.  
**Sumit Malhotra:** Thank you so much, sir.  
**Vishal Reddy:** Thanks.  
**BoardRoom\_FS Conf Room:** Thank you.  
**Vishal Reddy:** Thank you.  
**BoardRoom\_FS Conf Room:** Uh perh uh I think you're trying to go through some flow.  
**Parvesh Reddy:** Yes.  
**BoardRoom\_FS Conf Room:** Can you just start from again so that now I have a better  
**Parvesh Reddy:** Okay.  
**BoardRoom\_FS Conf Room:** perspective?  
**Parvesh Reddy:** So essentially when we start off the projects uh the requirement was um they are bu they're looking at EVs for their projects and each exosome has uh some function and that function is dependent on which cell releases the  
**BoardRoom\_FS Conf Room:** Uh,  
**Parvesh Reddy:** exoome.  
**BoardRoom\_FS Conf Room:** one second. Again, you have to start. I'm just trying to figure out something here  
**Parvesh Reddy:** Sure.  
**BoardRoom\_FS Conf Room:** again.  
**Parvesh Reddy:** So the exoome they're looking at exosomes for research purposes and what the function of the exoome is dependent on which cell releases it and when it releases the cell uh sorry when it releases the exoome.  
   
 

### 00:53:14

   
**Parvesh Reddy:** So each exosome coming from each cell is uh has a different cell membrane that is coating it. So what they do is they need to see size. They need to see what proteins are coating the exoome so that they can figure out which exosome and where it came from. That is their um ultimate process at least ultimate requirement. So for now they have two machines that are currently looking at size and protein markup. That is uh what is the size of the exoome and what is the protein that is surrounding it. So to figure out the size they're using Zeta view which is the NTA machine nanop particle tracking and uh that basically they're taking that entire sample size they have they'll put one in this machine the machine will go through each particle uh it'll look at Brownian motion or something uh related to Brownian motion and take like snapshots to decide okay um it is these many particles are there in this area and then it'll extrapolate outwards. It'll only give an output.  
**BoardRoom\_FS Conf Room:** Okay.  
   
 

### 00:54:27

   
**Parvesh Reddy:** It doesn't show us that uh snapshot but it'll give us an output saying these are the values you're  
**BoardRoom\_FS Conf Room:** Okay.  
**Parvesh Reddy:** getting. These are how many particles we are expecting to see in this square inch area.  
**BoardRoom\_FS Conf Room:** Hold on. I think I may have a few more questions. Uh Michelle,  
**Parvesh Reddy:** Yeah.  
**BoardRoom\_FS Conf Room:** are you in sync with what is saying? because I have some  
**Vishal Reddy:** Yeah. Yeah. And uh yeah know I understand.  
**BoardRoom\_FS Conf Room:** advant  
**Vishal Reddy:** Uh so Pish my question is so when they look at the number of proteins that are surrounding this particular uh exoome or in terms of the size so is it does it mean that uh the higher the number of proteins the more effective that exoome is  
**Parvesh Reddy:** No, no, it's not looking at number of proteins.  
**Vishal Reddy:** or what protein is quoting it?  
**Parvesh Reddy:** It's looking at what protein it is. Yeah. So,  
**Vishal Reddy:** Okay.  
**Parvesh Reddy:** it's like one membrane can have multiple proteins and it it need not be the same.  
   
 

### 00:55:17

   
**Parvesh Reddy:** So, what they do is they add protein markers which are sensitive to some color. So that will come in the next machine, the flowcytometry machine. I'll go into detail once I get to that machine.  
**Vishal Reddy:** Okay. Okay. And uh in terms of you said it's giving a snapshot in terms  
**Parvesh Reddy:** No, it's looking at a snapshot,  
**Vishal Reddy:** of it's text.  
**Parvesh Reddy:** but it's just giving us an output in text saying Yeah.  
**Vishal Reddy:** So if you want huh go ahead.  
**Parvesh Reddy:** So,  
**Vishal Reddy:** Sorry.  
**Parvesh Reddy:** it just says like there are 50 particles of uh 40 nanometers in like one cubic cm.  
**Vishal Reddy:** Okay. And if you wanted to get to be able to visualize it, then we use that alpha fold kind of tool.  
**Parvesh Reddy:** No, no,  
**Vishal Reddy:** Is that correct?  
**Parvesh Reddy:** that is for the other project.  
**Vishal Reddy:** Oh, that's for the peptide uh project.  
**Parvesh Reddy:** Yeah,  
**Vishal Reddy:** Okay. Do they want to visualize this?  
**Parvesh Reddy:** not here.  
**Vishal Reddy:** I mean any tools they Okay.  
   
 

### 00:56:11

   
**Parvesh Reddy:** This tool they're building just for guidance. They don't want to do any in in uh they don't want too much insights or because they don't want their uh um their research to get um biased basically. So it's just for  
**Vishal Reddy:** Okay. Okay.  
**Parvesh Reddy:** guidance.  
**BoardRoom\_FS Conf Room:** Do do we have any uh document about this tool kesh that is what is the objective of this tool what they're trying to do  
**Parvesh Reddy:** Huh? Uh,  
**BoardRoom\_FS Conf Room:** and  
**Parvesh Reddy:** there's a tech requirements file I've made on u the Google  
**BoardRoom\_FS Conf Room:** oh Okay,  
**Parvesh Reddy:** Drive.  
**BoardRoom\_FS Conf Room:** probably you can share that folder and uh so that has the purpose of this tool what we are trying to do and what it what is our approach to solve this uh to  
**Parvesh Reddy:** Yes.  
**BoardRoom\_FS Conf Room:** build this tool.  
**Parvesh Reddy:** Yes.  
**BoardRoom\_FS Conf Room:** Okay.  
**Parvesh Reddy:** There is that file.  
**BoardRoom\_FS Conf Room:** And  
**Parvesh Reddy:** There is a architecture file and there is an architecture diagram that I've made. So all three are  
   
 

### 00:57:08

   
**BoardRoom\_FS Conf Room:** okay. Okay.  
**Parvesh Reddy:** there.  
**BoardRoom\_FS Conf Room:** Fine. Actually what we will do parish maybe we'll spend some time tomorrow. Okay. And we will go through from the beginning.  
**Parvesh Reddy:** Huh?  
**BoardRoom\_FS Conf Room:** Let me just look at it because I wanted to now get a complete understanding of what is it and where are we on this. So maybe we'll just take a break now and we will go to the complete understanding.  
**Parvesh Reddy:** Okay.  
**BoardRoom\_FS Conf Room:** uh tomorrow. I'm just trying to find uh no that's  
**Parvesh Reddy:** Would you like me to come to FS?  
**BoardRoom\_FS Conf Room:** uh let me just check.  
**Vishal Reddy:** No, I think we can do it virtually. That's fine.  
**BoardRoom\_FS Conf Room:** Yeah, let me Yeah,  
**Parvesh Reddy:** Okay.  
**BoardRoom\_FS Conf Room:** I think tomorrow is there are some things. Yeah, tomorrow afternoon. I think I'm flexible at this stage. You can uh go ahead and set up some time. I will just let you know whether we will do it in the office or we'll do it virtually.  
   
 

### 00:57:59

   
**BoardRoom\_FS Conf Room:** It doesn't matter.  
**Parvesh Reddy:** Okay, I'm I'm in a nut anyway, so I can just come  
**BoardRoom\_FS Conf Room:** Yeah, I I'll just let you know exactly if that's not an issue. Tomorrow afternoon,  
**Parvesh Reddy:** back.  
**BoardRoom\_FS Conf Room:** whatever works for you. No. Uh one generic question is I think she's talking about agentic. Why can't we use Salesforce?  
**Parvesh Reddy:** Um because none of this data is in Salesforce, so it's coming from outside. Then we'd have to create an organization for each of these objects and then it should store each of them in like a location. It it'll be too uh messy. If if the data was coming from Salesforce, it would make sense. But right now, since everything is external and it's not necessary that the user who's coming has Salesforce as uh their augle. So unless we'll be paying for Salesforce and putting each object  
**Vishal Reddy:** H.  
**Parvesh Reddy:** together.  
**Vishal Reddy:** So the all this data would have to be stored in like a Salesforce product,  
**BoardRoom\_FS Conf Room:** Okay.  
   
 

### 00:59:09

   
**Vishal Reddy:** right? Like a data cloud.  
**BoardRoom\_FS Conf Room:** No, actually.  
**Parvesh Reddy:** Yeah.  
**BoardRoom\_FS Conf Room:** Okay. So, those thoughts, you'll probably park it now. um in terms of the current AI chat interface that she's referring to.  
**Parvesh Reddy:** It is there actually but Sumit didn't show you.  
**BoardRoom\_FS Conf Room:** Uh oh,  
**Parvesh Reddy:** It's actually in the bottom.  
**BoardRoom\_FS Conf Room:** in the same uh  
**Parvesh Reddy:** Yeah, it's there in that in that uh dashboard only.  
**BoardRoom\_FS Conf Room:** demo  
**Parvesh Reddy:** But if you go in the bottom, he didn't show you. It's it's there in the bottom. So there is a chat interface.  
**BoardRoom\_FS Conf Room:** I  
**Parvesh Reddy:** Once we connect the AI, then uh the user will be able to say things like can you show me these graphs and it'll populate those graphs.  
**BoardRoom\_FS Conf Room:** I see. Okay. And what is that? So he built that user interface using Python right  
**Parvesh Reddy:** Correct.  
**BoardRoom\_FS Conf Room:** now.  
**Parvesh Reddy:** So initially we started with streamllet in Python.  
   
 

### 00:59:59

   
**BoardRoom\_FS Conf Room:** Okay.  
**Parvesh Reddy:** It's it's like a data it's a Python library but it it kept forgetting data once we switched tabs and things like that. So we switched to React that is also in Python.  
**BoardRoom\_FS Conf Room:** Okay. Okay.  
**Parvesh Reddy:** So eventually what we'll end up doing is we'll sort of package it to like an EXE file or something so  
**BoardRoom\_FS Conf Room:** Fine.  
**Parvesh Reddy:** that people can use it directly. It'll be like an installation file. You can install it as a  
**BoardRoom\_FS Conf Room:** Okay.  
**Parvesh Reddy:** software.  
**BoardRoom\_FS Conf Room:** Now I'm just asking again a basic question. If uh you know why can't we use Tableau for the visualization?  
**Parvesh Reddy:** Um there's no requirement to use Tableau uh cuz it's directly showing up through Python  
**BoardRoom\_FS Conf Room:** Okay. Okay.  
**Parvesh Reddy:** itself.  
**BoardRoom\_FS Conf Room:** Cuz my understanding is uh some of the customers I have seen them using Tableau for these type of analysis. Uh  
**Parvesh Reddy:** But uh problem is in Tableau you'll have to put the data in yourself.  
   
 

### 01:01:07

   
**Parvesh Reddy:** you. We can't do it from  
**BoardRoom\_FS Conf Room:** Now if there's a assume there's again you know data cloud  
**Parvesh Reddy:** outside  
**BoardRoom\_FS Conf Room:** right data cloud connecting to Tableau and then we can just uh visualize it and use the Tableau interface  
**Parvesh Reddy:** then we'd have to give access to Tableau that time. Here they don't need any extra access. they can just it'll just show up on the UI but at that point we'll have to give like a Tableau license for them to look at it and uh like if they want to change anything on it they'll need to have like those  
**BoardRoom\_FS Conf Room:** Uh sure I understand.  
**Parvesh Reddy:** accesses  
**BoardRoom\_FS Conf Room:** So keeping that uh license part aside is it going to give a better experience from the business perspective. Okay. Uh let me say that you know is it going to give them a more value will park the license aside.  
**Parvesh Reddy:** Mhm.  
**BoardRoom\_FS Conf Room:** Do you do you see that you know? Yeah.  
**Parvesh Reddy:** I honestly will think this uh native UI is better um because this is very customizable.  
   
 

### 01:02:21

   
**Parvesh Reddy:** If it was uh any other kind of requirement uh which is a little more businessoriented, it's okay. we can consider it but as a scientific research related tool it's easier to have a more customiz because even if they come later for more features we can we can probably code it in at some point but this way even pushing new ideas new things it'll be difficult through Salesforce  
**BoardRoom\_FS Conf Room:** Okay. Yeah. just out of curiosity uh I was just uh you know checking you know why not this versus by the homegrown custom right that that's the thought process and uh you know are there any other better tools that will give us an advantage keeping you know option A is Python and let's say you know whatever we are doing it option B is Tableau Salesforce option C are there any other better tools designed for this purpose  
**Parvesh Reddy:** There are some other uh script coding uh languages we can use but uh Python is sort of the simplest we can use right now. Uh maybe at some point we can migrate to another one but right now this would be the quickest way we can program.  
   
 

### 01:03:39

   
**Parvesh Reddy:** We need more specialized people for other uh  
**BoardRoom\_FS Conf Room:** You can just think and give me you know summary thought whenever you get a chance.  
**Parvesh Reddy:** uh  
**BoardRoom\_FS Conf Room:** It's not that we have to do it tomorrow. Uh but I I just wanted to make sure that you know uh if I if we need to say package this and uh we have to apply it elsewhere you know what is the best way of doing it.  
**Parvesh Reddy:** So ideally to package this and use it elsewhere what we were thinking is this entire tool itself can be packaged directly like it'll come as an app that you can directly log to. So you just open the app and you put your uh credentials in and it'll log in. So that's the kind of functionality we're looking at right now.  
**BoardRoom\_FS Conf Room:** And let's say if the input file formats are they are not FCS if they let's say I decide to use seams device I'm just giving you for the sake of argument and semons generates that data in some other format.  
   
 

### 01:04:44

   
**Parvesh Reddy:** So right now the functionality is there for FCS,  
**BoardRoom\_FS Conf Room:** man.  
**Parvesh Reddy:** PDS, TXT, image and u CSV and  
**BoardRoom\_FS Conf Room:** Okay.  
**Parvesh Reddy:** Excel.  
**BoardRoom\_FS Conf Room:** Okay.  
**Parvesh Reddy:** So if  
**BoardRoom\_FS Conf Room:** So you that will that will cover all the instruments out there in the  
**Parvesh Reddy:** someone Yeah,  
**BoardRoom\_FS Conf Room:** industry.  
**Parvesh Reddy:** usually something will get output generally as either FCS or CSV. Um we've added a few more but these are the two that you'll usually get a tabular format  
**BoardRoom\_FS Conf Room:** Okay,  
**Parvesh Reddy:** in.  
**BoardRoom\_FS Conf Room:** understood. And that streams was it a sufficient from uh the biompt initially to use that?  
**Parvesh Reddy:** Streamlate didn't come from bioarm. It's something we decided to use  
**BoardRoom\_FS Conf Room:** Okay. Okay.  
**Parvesh Reddy:** initially.  
**BoardRoom\_FS Conf Room:** And what were they doing it for the previous analysis?  
**Parvesh Reddy:** Previously now they have now they're doing everything manually. So they're once they populate the graphs using their uh machine they're looking at it physically.  
**BoardRoom\_FS Conf Room:** Oh, this kind of  
**Parvesh Reddy:** They have no Yeah. So for them it's like they're printing out the TX the outputs.  
**BoardRoom\_FS Conf Room:** thing.  
**Parvesh Reddy:** They're looking at um each of the machine outputs directly and doing it.  
**BoardRoom\_FS Conf Room:** Okay. Okay. And the person who is involved, what's his name? I'm concerned.  
**Parvesh Reddy:** Jagan and Surya both of them will be  
**BoardRoom\_FS Conf Room:** So so I remember I was using some software  
**Parvesh Reddy:** doing  
**BoardRoom\_FS Conf Room:** correct to do the analysis.  
**Parvesh Reddy:** that is native to the machine machine is done that yeah that's  
**BoardRoom\_FS Conf Room:** Oh the machine gives something.  
**Parvesh Reddy:** coming from the  
**BoardRoom\_FS Conf Room:** Okay.  
**Parvesh Reddy:** machine  
**BoardRoom\_FS Conf Room:** And he does he never developed anything in Python or anything of this  
**Parvesh Reddy:** nothing they have some uh Surya is doing some work with uh  
**BoardRoom\_FS Conf Room:** file.  
**Parvesh Reddy:** for the peptide stuff he has  
**Vishal Reddy:** Sure. We'll catch up tomorrow.  
   
 

### Transcription ended after 01:07:09

*This editable transcript was computer generated and might contain errors. People can also change the text after it was created.*

Dec 5, 2025

## Biovaram UI improvement and calculation changes \- Transcript

### 00:00:00

   
**Parvesh Reddy:** So, how's your day?  
**Sumit Malhotra:** Uh, it's going good.  
**Parvesh Reddy:** Very good. So, shall we start?  
**Sumit Malhotra:** Yeah. Yeah, we can.  
**Parvesh Reddy:** Can you pull up the UI?  
**Sumit Malhotra:** Sure.  
**Parvesh Reddy:** I just have a few changes I wanted done.  
**Sumit Malhotra:** Sure. Just Mhm. Just a moment. Uh, I believe UI is visible.  
**Parvesh Reddy:** Yeah. Do you want to record the session? Just so you can remember recording.  
**Sumit Malhotra:** Yeah, just a second. Manage recordings.  
**Parvesh Reddy:** Yeah. Yeah, it's recording.  
**Sumit Malhotra:** Okay. Okay, great. So, I'll share the screen.  
**Parvesh Reddy:** This is how I look, by the way. I don't think you've seen seen me before.  
**Sumit Malhotra:** Yeah. So, here it is.  
**Parvesh Reddy:** Okay. So what I wanted done is um to start off with if you go down to where the graphs are put up right for the cytometry down.  
**Sumit Malhotra:** Mhm. Mhm. Cytometry tab aka here.  
**Parvesh Reddy:** Okay, the graph is not here but um  
   
 

### 00:01:38

   
**Sumit Malhotra:** I'll I'll do that. We can just simply pull one analysis and graphs and all the things. Okay. So now graphs are here as well.  
**Parvesh Reddy:** Yeah. So if you see here um the bottom graph particle size distribution see most of them are in 40 and most of them are in 180\. This is actually because everything beyond the range is getting uh set to 40  
**Sumit Malhotra:** Mhm. Mhm.  
**Parvesh Reddy:** and 180\. So we need to have that not do that cuz then it's affecting the distribution.  
**Sumit Malhotra:** Mhm. Okay.  
**Parvesh Reddy:** So what I suggest is um we can extend the range to say uh 30 to 220 or something diameter search range.  
**Sumit Malhotra:** So basic. Mhm. Okay. Mhm.  
**Parvesh Reddy:** Everything 30 and below or everything 30 you just don't show it.  
**Sumit Malhotra:** Mhm. Okay.  
**Parvesh Reddy:** And we can only show 40 to 180\. greater than 220\.  
**Sumit Malhotra:** Okay. So, basically here we need to just uh change the range a little bit. We we will not be showing smaller than 30 and uh maximum greater than 20\. Okay.  
   
 

### 00:03:10

   
**Sumit Malhotra:** And for the show purposes also this range will be considered or 40 to 180 is fine.  
**Parvesh Reddy:** 40 to 80 is enough because um 40 to 200 because he said 40 to some range he gave no yesterday.  
**Sumit Malhotra:** Okay. Mhm. 200\. Yes. 200 he said in the meeting right yesterday.  
**Parvesh Reddy:** Yeah. So he he gave a different range right he gave like three buckets. Do you have 50 to 100 100 and 200?  
**Sumit Malhotra:** Yes. Yes. One is less than 50\. One is 50 to 200 and one is 200 and above. 200\. Okay.  
**Parvesh Reddy:** I think he said 50 to 100, 100 to 200, right? That's what he said.  
**Sumit Malhotra:** Like when he was explaining from that uh document or what he was showing that time. So in that he is filtering out like less than 50 greater than 200 and in between 50 to 200\. So that what I look because I after that I read the transcript as well complete transcript. So in that it is also mentioned like these three ranges that I'll do.  
   
 

### 00:04:10

   
**Parvesh Reddy:** So then what we'll do is let's have it as um 30\. Remove anything below 30\. Okay. So then uh 40 to let's have it as proper ranges. Let's have 40 to 80, 80 to 120\. Oh, maybe we can have bigger ranges.  
**Sumit Malhotra:** Mhm. Mhm.  
**Parvesh Reddy:** Let's have like 40 40 split.  
**Sumit Malhotra:** What? Yeah.  
**Parvesh Reddy:** 40 to 100\. Sorry, 60 split, right?  
**Sumit Malhotra:** Yeah. So, what? Mhm. Mhm.  
**Parvesh Reddy:** 40 to 100, 100 to 160, 160 to Yeah, but we're removing 220\. So 60 to 200 is fine.  
**Sumit Malhotra:** 160 and 160 to 220\. Okay. Because uh what I was thinking is like let's say we have there here is a size range analysis, right?  
**Parvesh Reddy:** H.  
**Sumit Malhotra:** So these are actual filters that we can apply basically. Right? Now as you can see there are filters coming along 30 to 100, 100 to 150 or either 40 80 these filters. So we can just put up a column here while the person is doing the analysis either we can we can set it as default like whatever we discussed that is okay but if the person want to change that as well.  
   
 

### 00:05:22

   
**Sumit Malhotra:** So we can simp yeah simply here and it will click and the graphs will change according to that because I added after that this 50 200 and this thing.  
**Parvesh Reddy:** Ah, you can have them enter it here. That's fine. Huh? That's also fine. Yeah, we can do that way also.  
**Sumit Malhotra:** So when we apply that so I believe the graphs will change right here you can see so graphs that is why I implement interactive graphs in it so that whenever anybody wants to change the graphs or realtime evaluation  
**Parvesh Reddy:** Yeah.  
**Sumit Malhotra:** they can just simply choose the filters and check for the datas as well.  
**Parvesh Reddy:** But you should do one thing here. When when you're picking the range there, it's showing uh the numbers here.  
**Sumit Malhotra:** Mhm.  
**Parvesh Reddy:** But then it's not uh I don't think it's changing the diameter search range.  
**Sumit Malhotra:** Yeah, that that we have to like as I mentioned that we have to fix like to the default when the actual calculation is happening at first then it will do that at that moment only sure yes yes I'll  
   
 

### 00:06:17

   
**Parvesh Reddy:** Okay. So have it match the diameter search range to match the filter.  
**Sumit Malhotra:** do Mhm.  
**Parvesh Reddy:** Uh basically it should be little more than filter and then remove the last few and then another thing was uh the mean median size right this mean and median is getting skewed because of those values those the other  
**Sumit Malhotra:** Yes. Yes. Yes. Understood. Mhm.  
**Parvesh Reddy:** values. So you need to have this only calculate like uh once you have the neglecting the larger like 30 and 200 have it calculate only between those other numbers.  
**Sumit Malhotra:** Yes. Yes. Mhm. Mhm. Okay.  
**Parvesh Reddy:** So you're now right now we have 40 to 200, right?  
**Sumit Malhotra:** Yes.  
**Parvesh Reddy:** And you're taking 30 extra and 200 extra and you're going 220 extra and you're going to neglect those.  
**Sumit Malhotra:** Okay.  
**Parvesh Reddy:** So the median should be calculated between greater than 30 up to less than 220, right?  
**Sumit Malhotra:** And then 200 220 sorry okay got it and uh what I did is like as we have mentioned uh I removed this uh main  
   
 

### 00:07:24

   
**Parvesh Reddy:** Yeah. Less than 200\. Yeah. So for between 40 and 200 it should calculate the median.  
**Sumit Malhotra:** showing here and I removed that part but I kept it into the back end for the modeling purposes that the graphs we made or the models that we created. So for that we kept it but for the show purposes on the UI we just showing now the median D50 diameter nanometers and the standard deviation.  
**Parvesh Reddy:** Oh, that's fine. I mean, that depends. They can put whatever they want. So, it's up to them to decide.  
**Sumit Malhotra:** Yeah that is that is actually like but for now because ultimately until and unless we are not getting the best practices for each and everything we can't uh just judge what they actually want or what they want to  
**Parvesh Reddy:** So, yeah, we kind of just Yeah.  
**Sumit Malhotra:** see. So whatever we can understand from the data we can just put it right now across it and we can just show them that this is what we understand and if there are any changes they can just adjust us  
   
 

### 00:08:26

   
**Parvesh Reddy:** And one more uh I want have you um put the any functionality for picking and choosing between VSSsc 1 and VSSSC 2\.  
**Sumit Malhotra:** and so uh basically you are ask uh saying like uh automatically picking right.  
**Parvesh Reddy:** Huh. Basically it should uh decide on whichever is larger. Maybe you can have it create an extra column in the back end.  
**Sumit Malhotra:** Mhm.  
**Parvesh Reddy:** where it is selecting the larger of VSSSE 1 or VSSSE2 not like what I wanted to  
**Sumit Malhotra:** I believe it do like basically here it show that auto selected SSC column VSSC1 H highest median because it calculates the median of that and it automatically select that and in the FCS column there is Mhm.  
**Parvesh Reddy:** do is create a new column and then you say VSSSE max and let it look at uh the VSSSE 1 H and VSSSE 2 H and pick whichever the larger one is and then fill that column with that  
**Sumit Malhotra:** Mhm. Mhm. Mhm.  
**Parvesh Reddy:** number and then it should use that to calculate the uh size of the exosome  
   
 

### 00:09:36

   
**Sumit Malhotra:** Okay. Yeah. So see that's that's what actually at the basic level it is actually doing right. As you can see like here is a graph that data that we pulled up from the fax file. Now in the VFSC1 maximum in the maximum of the cases VSSSC1H is the bigger in size right and that is where it is get selected but I will look into it and make it more robust where it will be actually calculating properly all the things between these two whatever the max is there it will be picking up and applying it here and for similar for the similar it is doing for the FSC column as well.  
**Parvesh Reddy:** FSE is just one column, right? So it doesn't matter.  
**Sumit Malhotra:** Yes, that is why it is uh showing layer detecting single FSC column and it is putting it up here.  
**Parvesh Reddy:** Okay. Okay.  
**Sumit Malhotra:** Yeah.  
**Parvesh Reddy:** So yeah, it was those two changes. Apart from that, uh do we does this site have like a light mode?  
**Sumit Malhotra:** Mhm.  
   
 

### 00:10:35

   
**Sumit Malhotra:** Light mode. I don't think so at the moment. I'll add it. That is just color changing thing that we need to maintain.  
**Parvesh Reddy:** Just just because like Yeah, cuz um from what like right now it's just dark, right?  
**Sumit Malhotra:** We need to decide the color palette. We need to decide the color palette for it.  
**Parvesh Reddy:** Some people might not like it like this.  
**Sumit Malhotra:** Yes. Yes. Yes. Because and one more thing is there like in in the streamllet UI what I experienced is because I I never worked with streamllet to be very honest. I I usually do all my front end either in react either in Typescript either in Vue.js GS that is my yes yes yes that's what I'm telling like I never worked with stream but I faced few issues that  
**Parvesh Reddy:** We can switch to that. That's fine. We just started with this because this is what I knew.  
**Sumit Malhotra:** I analyzed in streamllet because what happens is uh let's say uh when we are on a flow seyometry tab and now let's say as as I enter the functionality where cross comparison can be done right so now if  
   
 

### 00:11:33

   
**Parvesh Reddy:** H. Okay.  
**Sumit Malhotra:** I go to the cross comparison tab and come back to the flow seytometry tab again it will not contain the state of that I added the state management as well but sometime it lose the state in between in streamline because let's say what it do is with the state management what I able to do like let's say there is a full explanation and full analysis right now here right now after that when I go to here it will be just saving the cached version of that a small version with a little brief that a user can see not the full analysis so that what I was thinking how to implement in streamllet I was searching that but I'll do that basically not a big issue but still there is one issue that I noticed in streamlet that it happens state management is very complicated here I'll I was trying because what what usually I do  
**Parvesh Reddy:** Okay. Yeah. But if you feel something else is better, you go ahead. We can switch to that.  
**Sumit Malhotra:** is for the basic prototyping of anything in the react I'll just simply go to this vdev so basically it is an AI powered tool which can create beautiful templates for our react.  
   
 

### 00:12:41

   
**Sumit Malhotra:** Basically, we just have to explain the scenario and it can create a basic structure with the modern TypeScript or React UI and we can further enhance it ourselves. So, it can give us a better idea. So, what I'll do is I'll run this agent once today and after that I'll share you the results. If that is looking good enough, we can just go on with the further uh you can say improvements as well.  
**Parvesh Reddy:** Yeah, that's fine. I have meetings till what time? One second. till uh 2:00 and then I have another meeting at 7:30.  
**Sumit Malhotra:** Mhm.  
**Parvesh Reddy:** So between 2 and 7:30 I'm free.  
**Sumit Malhotra:** Okay. Okay.  
**Parvesh Reddy:** I'll just Yeah, sure.  
**Sumit Malhotra:** No issues. I'll I'll do that basic prototyping in between that time. But after two, I will just uh reach out once to you and we can just simply connect for 5 10 minutes and we can review the reactor or TypeScript UI. The basic prototype that we are able to achieve. Any other things of wish?  
   
 

### 00:13:38

   
**Parvesh Reddy:** Uh no, just these changes.  
**Sumit Malhotra:** Okay, I'll make that.  
**Parvesh Reddy:** Cool. Oh, there's no need to put up one meeting also.  
**Sumit Malhotra:** I can't just show my camera right now because I have so many dogs on in my room. I just can't. I have seven pet dogs.  
**Parvesh Reddy:** Oh, okay.  
**Sumit Malhotra:** The two are sleeping besides my table on my bed.  
**Parvesh Reddy:** How do you manage so many dogs, dude?  
**Sumit Malhotra:** Basically what happened is there like we have lots of street dog in the outer street out of our so one of like we just used to feed them previously.  
**Parvesh Reddy:** Okay.  
**Sumit Malhotra:** So after that what happened is uh one of them gave birth to um puppies. So it was a winter time last year and then she was afraid that puppies will die.  
**Parvesh Reddy:** So, this came home.  
**Sumit Malhotra:** So she came it like here because we have a store room outside our house that is in the outer veranda. So he just keep the puppies there for the bomb and after that when they are staying here inside then they become here only.  
   
 

### 00:14:50

   
**Sumit Malhotra:** Now they're living here.  
**Parvesh Reddy:** They just took over your house. I don't have any pets here. My wife has a dog, but it's in the village.  
**Sumit Malhotra:** Oh, so you are living in Bangalore, right?  
**Parvesh Reddy:** I technically am for now but I will at some point start working from home.  
**Sumit Malhotra:** Okay.  
**Parvesh Reddy:** Right now I'm at at home. This is my house in Chennai.  
**Sumit Malhotra:** Okay. You are from Chennai.  
**Parvesh Reddy:** Yeah.  
**Sumit Malhotra:** Okay.  
**Parvesh Reddy:** So I'll be here till Monday.  
**Sumit Malhotra:** So how is your weather here? Bangalore weather. I know Bangalore weather. So I lived Bangalore for two years. So I know Bangalore weather.  
**Parvesh Reddy:** Chennai is generally hot but today it's very pleasant like it's I'm only running with the fan. Usually you need the AC but today just just the fan is fine.  
**Sumit Malhotra:** We can't think of fans or anything in December here.  
**Parvesh Reddy:** Oh Hannah.  
**Sumit Malhotra:** Yeah. We like in my where I live in Hana.  
   
 

### 00:15:54

   
**Sumit Malhotra:** So the average temperature keeps between in winter at this moment at night it will go down to 2 or 3°C in day 10 12 15 north no just aside Punjab we are like a land based  
**Parvesh Reddy:** Okay. Yeah. Hyana is um it's it's on a hill, right?  
**Sumit Malhotra:** area basically Himachel is on hills so here the temperature shifts suddenly That is why I had a sore throat previously.  
**Parvesh Reddy:** Oh, okay. Oh, okay. Yeah. Yeah. Temperature. But uh do you is it like dry there or uh  
**Sumit Malhotra:** Ah it is like it is actually we have all the extreme weathers. If there is a summers then there will be extreme summers. Temperature goes up to 50°C 52°C. If there are winters then the temperature is extreme winters. We can go as below as 0°C. The the snowfall don't happen here but the temperature can go up to zero.  
**Parvesh Reddy:** and go  
**Sumit Malhotra:** The fog is the main concern because when the winters came in the evening and in the morning there are complete fog. You can't see even 10 ft in front of you if  
   
 

### Transcription ended after 00:17:11

*This editable transcript was computer generated and might contain errors. People can also change the text after it was created.*

Dec 3, 2025

## Biovaram Weekly Customer Connect.  \- Transcript

### 00:00:00

   
**Sumit Malhotra:** Praise.  
**Parvesh Reddy:** Hi, how are you?  
**Sumit Malhotra:** I'm good. How are you?  
**Parvesh Reddy:** I'm good. Um, I'm audible, right?  
**Sumit Malhotra:** Huh?  
**Parvesh Reddy:** Okay.  
**Sumit Malhotra:** You are audible.  
**Parvesh Reddy:** Okay. Let's just wait another few minutes.  
**Sumit Malhotra:** Sure. Sure. Sure. My shoes.  
**Parvesh Reddy:** Um, I think is off.  
**Sumit Malhotra:** So, h why is this on a holiday?  
**Parvesh Reddy:** I think it's his sister's wedding or something. He said, "Yeah, you were about to ask something."  
**Sumit Malhotra:** Okay, that's great. I uh sorry.  
**Parvesh Reddy:** You said you were about to ask something.  
**Sumit Malhotra:** Uh no, no, I'm not asking. I'm just uh like testing the front end and everything by sitting before presenting it because I made multiple changes.  
**Parvesh Reddy:** Okay. Okay. Okay. Mhm.  
**Sumit Malhotra:** So now it is looking a bit better as well in terms of graphs and everything as well.  
**Parvesh Reddy:** Okay. Can we uh get the functionality of pinning the graphs to the dashboard from first page?  
   
 

### 00:01:52

   
**Sumit Malhotra:** So basically when the graphs are created so that can be shifted to the dashboard right.  
**Parvesh Reddy:** Correct.  
**Sumit Malhotra:** Okay. Uh I will look into it. I will it it is possible like basically we can just simply show the view on both the sides. It shall be it can be appeared it it will be appeared like on the fax one and as well as on the dashboard. So that the ultimate comparison. So basically you are asking for the comparison part right where we have multiple files and when we are doing the comparison.  
**Parvesh Reddy:** huh it's like no not multiple files but for the same file if they want to populate multiple graphs so they can create one graph pin it it'll stay there cached and if they generate another graph that will still  
**Sumit Malhotra:** Got it. Got it. Got it. Yeah. I I'll look into it. Mhm. Got it. Got it.  
**Parvesh Reddy:** be there plus they can add this  
**Sumit Malhotra:** Got it. I'll do that.  
   
 

### 00:02:42

   
**Sumit Malhotra:** I'll I'll look into it. I'll see the pinning functionality into the dashboards so that the data will be cached. I I added some caching right now as well for the safe state of the graphs. I'll do that. I'll further enhance it.  
**Parvesh Reddy:** Okay.  
**Sumit Malhotra:** Basically, one more thing I added like the the in the requirement file that we have in which it is mentioned right the cross comparison function. I was trying to look into that like basically how we can do that when we have the proper data we can work up on this. So basically I added a tab of gross uh comparison as well. I'll show you just a second uh screen I believe screen is visible right so here it is.  
**Parvesh Reddy:** Yeah. Yeah.  
**Sumit Malhotra:** So basically now what it do is cross comparison tab here it is it looks something like this. So basically what we can do when we go to the flowcytometry we just uploaded a file and do the analysis what whatsoever we want to do right after doing so uh we get the analysis here then we go  
   
 

### 00:03:43

   
**Parvesh Reddy:** Mhm.  
**Sumit Malhotra:** to the nanop particle tracking and we can upload a file here as well and do the same thing and then it will take both of their tabs data into the cross comparison for the moment and check upon some things which are mentioned in the so I created a little bit of comparison model it is not completed yet but it will be because the ultimately what whatever the back end part that we can do till yet we  
**Parvesh Reddy:** Okay.  
**Sumit Malhotra:** completed that already. So I was just looking into additional features h because when we get the AI thing and then we can start creating model accordingly and all the other files that is required for that training purposes.  
**Parvesh Reddy:** Now we're just waiting on the Yeah, now we're just waiting on the AI thing. Yeah, we can.  
**Abhishek Reddy:** Did T me respond on that license part?  
**Parvesh Reddy:** No, I didn't get anything.  
**Abhishek Reddy:** We'll ask her to stay on the call.  
**Parvesh Reddy:** I thought maybe she I thought okay I've messaged her in Google chat also like personally  
   
 

### 00:04:49

   
**Abhishek Reddy:** We'll ask her to stay on the call. After the client, right, in the same meeting, we can ask her to continue. I ping her on WhatsApp also. Let me call and remind her. I'm sure she would have forgotten. Yeah,  
**Parvesh Reddy:** because I thought maybe she might have missed it on the group so I put it for her personally also.  
**Sumit Malhotra:** Moreover, one more thing I did uh previously when we created the graphs, we are just creating a simple graphs like with mattplot.lib that is static graphs. So I just changed that with plotly. So now the graphs are also interactive. If anybody wants to interact with the graphs, they can do that.  
**Parvesh Reddy:** But you had mentioned we want you wanted to switch to React, right?  
**Abhishek Reddy:** she'll join here.  
**Sumit Malhotra:** uh me shifting to react uh because uh see u I had a conversation with Mohit.  
**Parvesh Reddy:** That is uh the stream lit. Instead of using streaml  
**Sumit Malhotra:** So Mohe told me that uh right now I didn't checked any of that part in the react.  
   
 

### 00:06:00

   
**Sumit Malhotra:** So he said that I am not that versatile enough. So I told him that I will create one um you can say basic functionality dashboard into the react and I'll present it to you guys. So like whichever we feels is looking better we can use that but for now as we already showed the streamllet one so I just integrated all the features just to showcase the functionality into the streamlet itself. I am working upon that react part as well. He when when whence it is completed I'll I'll share that thing with you that it is looking like this now a little bit more.  
**Parvesh Reddy:** Okay.  
**Abhishek Reddy:** We'll continue the call with Char after the client call. Yeah, Char.  
**Parvesh Reddy:** Yeah.  
**Abhishek Reddy:** After the client call, we'll continue in the same call. Yeah, just letting I think we can discuss since they have not yet joined anything.  
**Charmi Dholakia:** Yeah. Yeah. Okay.  
**Sumit Malhotra:** Mhm.  
**Parvesh Reddy:** I mean yeah so I spoke to IT team what uh they are saying is uh as while we're using AWS for everything we use basically sending a prompt receiving data everything we'll get charged so they want  
   
 

### 00:07:02

   
**Abhishek Reddy:** and the license. So you checked with IT team, right? You want to Have it.  
**Parvesh Reddy:** to know what are the features and like limits we get for a free account and if we need to pay for it, what exactly are we looking at for now? What limits we'll be placing? All the settings we'll need that they can purchase and what we'll need later separately.  
**Abhishek Reddy:** Yeah, because with one of our customer right they kind of enabled it and for every transaction I think it costed some laks of rupees like the the reser was not aware actually so they didn't know that and they were charged for a higher amount that's the reason they wanted to be double here because it's coming close to $5,000, right?  
**Parvesh Reddy:** Yeah. And like when we activate, when we deactivate, they want all those details.  
**Abhishek Reddy:** Per annually. Let's bring Sumit here. Not Sumit, sorry, Surya. Parish remainder 5 minutes then we can continue whatever we wanted to check which mo is on  
**Parvesh Reddy:** Yeah, I'll message.  
   
 

### 00:08:25

   
**Charmi Dholakia:** all the things which it requires now you can just put it in a ping and let me know which I'll give the thanks  
**Parvesh Reddy:** Uh, Surya said he'll join in five minutes. Yeah, I've I've sent a Google message to you with the details.  
**Abhishek Reddy:** leave by the way. Yeah.  
**Charmi Dholakia:** Okay. Okay. I'll just check. Huh? Yeah, I have received. Okay.  
**Parvesh Reddy:** Yeah. Yeah. Cuz I put on the group yesterday and then it just went up while we were discussing. So, I thought I'll send it to you separately.  
**Charmi Dholakia:** Okay. Yeah. Yeah, I have received it. Yeah. Okay. I'll just work on it and I'll let you know that Excel sheet.  
**Parvesh Reddy:** Yeah, if you can put it together in like a proper either like get us an estimate like the pricing thing that we did that day with all the settings or if you put it all together in a Excel sheet both either way will be fine but all of the details are not there in that Excel.  
   
 

### 00:09:29

   
**Charmi Dholakia:** What did the IT team tell on the Excel?  
**Parvesh Reddy:** like it's it's there, but then it's not like what you would see when you're purchasing a trade.  
**Charmi Dholakia:** Mhm. Yeah. Okay.  
**Abhishek Reddy:** Maybe open the purchase page now and select all those things and then uh yeah instead of you can go to the payment page and drop off and then take a screenshot and share that will help.  
**Charmi Dholakia:** Okay. Yes.  
**Abhishek Reddy:** We're trying to go with the minimal whatever is possible at least phase wise or whatever.  
**Charmi Dholakia:** Right. Yeah, I even I was thinking of free only, but we'll see what limits are there.  
**Abhishek Reddy:** Mhm. Yeah. Because they had already purchased one. I'm not sure whether we can purchase one more the free one.  
**Charmi Dholakia:** Yeah. Uh-huh.  
**Abhishek Reddy:** Yeah.  
**Charmi Dholakia:** Okay.  
**Parvesh Reddy:** Because from what um Sudhakar had mentioned yesterday is he said uh they can try to make a new account but if they use that then they might have some issues while giving the GST number.  
   
 

### 00:10:29

   
**Parvesh Reddy:** So he said we might have to purchase it as a personal account but even if we do it that way uh they're not sure what exactly to do. So he said uh give me these details and then from there I'll talk to you and uh the others.  
**Abhishek Reddy:** Mhm.  
**Charmi Dholakia:** Yeah, sure. I'll I'll give you the details.  
**Abhishek Reddy:** So any questions we have for Surya and Jaga today can because Moit is not here today.  
**Parvesh Reddy:** Yeah. uh just the fact that uh he needs to give us data. Other than that, we don't have any uh questions. We can show the updates we've done to the UI and back end. Um yeah, yeah, Sumit has it. He just showed me.  
**Abhishek Reddy:** Okay. Yeah. Someone wants to join the call.  
**Parvesh Reddy:** Yeah. Surya, sir. Is it Okay.  
**Abhishek Reddy:** Yeah.  
**Surya Pratap Singh:** Hi everyone.  
**Abhishek Reddy:** Hi. Hi.  
**Parvesh Reddy:** Hi.  
**Surya Pratap Singh:** Hi  
**Parvesh Reddy:** Uh, do you know if Jagen sir will be joining us?  
   
 

### 00:11:39

   
**Parvesh Reddy:** Oh, cuz he had mentioned as long as Surya Assur is here, he'll be fine.  
**Charmi Dholakia:** Yeah, I'm mute.  
**Abhishek Reddy:** Yeah.  
**Parvesh Reddy:** But he said he'll try to join. That's okay. Uh, Sumit, in the meantime, can you prepare the UI okay?  
**Surya Pratap Singh:** Sorry, I was muted and continuously speaking.  
**Abhishek Reddy:** Oh yeah.  
**Surya Pratap Singh:** Sorry. Yeah. Yeah, I texted him. Uh maybe if I am in a meeting. Okay. So, he will not be able to join again.  
**Abhishek Reddy:** Okay.  
**Surya Pratap Singh:** Okay. Yeah. Uh so there is some progress uh this week.  
**Parvesh Reddy:** Yeah.  
**Sumit Malhotra:** Ah, yes.  
**Parvesh Reddy:** So in terms of uh data, we were hoping you can give us the data at least this week or next week.  
**Surya Pratap Singh:** I'll give like uh uh at least uh uh NTA uh things are finalized and uh I'll give you uh some data. Nanoax they have just started. So uh I hope uh by the end of this week they will generate some useful data.  
   
 

### 00:13:32

   
**Surya Pratap Singh:** uh it is there at the uh you know experimental side people uh they are unable to generate data by this time.  
**Parvesh Reddy:** Okay.  
**Surya Pratap Singh:** Uh I hope uh this I mean last week they started the protocols everything so I think they will uh start generating data and they will be giving us something useful.  
**Parvesh Reddy:** Okay. Okay. Uh, Sumit, can you share?  
**Surya Pratap Singh:** So NPA part I will I will share  
**Parvesh Reddy:** Okay, sure. Uh, Sumit, can you share the UI?  
**Sumit Malhotra:** Uh yes. Yeah. So here is the UI that we updated basically. So there are multiple things that we attached and that we worked upon. One or the two things I'll show you. one is that is a requirement I believe you guys asked about the data that we need to take.  
**Parvesh Reddy:** Yes.  
**Sumit Malhotra:** So here it is these are the experimental condition data that we can logged here and it will be stored and give to the AI in future whenever the AI is incorporated into it right.  
   
 

### 00:14:37

   
**Sumit Malhotra:** So the factors and everything the settings we can select here or if any other settings that we need to add it here we can do that easily. truth. It is kind of a experimental condition section that we added. Now,  
**Parvesh Reddy:** So uh background for this was uh Jaganser had mentioned earlier this week that he wanted um the nanofax data the the nanofax experiment conditions to be compared with the AI  
**Surya Pratap Singh:** Yes.  
**Parvesh Reddy:** and best practices. this but huh but the thing is we don't have the data in the metadata or the uh file.  
**Surya Pratap Singh:** Yeah. Yeah. I remember. I remember. I was in that meeting. Exactly. Yeah. Unless you have the data you cannot I I I am aware I I spoke to him uh but uh even we had Saturday continuous two days uh meeting so we were unable to uh do anything useful. Uh I hope this weekend I will be able to uh provide some I as soon I get some uh tax data I will uh share you and maybe I'll speak to you in person.  
   
 

### 00:15:38

   
**Parvesh Reddy:** Yeah. So what we've decid what we've done for now is we've made a input box where the the user can input the experimental conditions that he used he or she used.  
**Surya Pratap Singh:** Yes. Yeah.  
**Sumit Malhotra:** and then we can just simply save this one. Right now it is not working as that. Just a second. I believe my back end stopped. Yes, just a sec.  
**Surya Pratap Singh:** Okay. So since we are meeting on uh uh office hours uh I can share something what I had I can show you something what I had worked upon last couple of weeks and uh uh this would be something they  
**Sumit Malhotra:** Mhm. Mhm.  
**Surya Pratap Singh:** will require. So please continue uh once you are done maybe last two three minutes I will share Mhm.  
**Sumit Malhotra:** Okay. Sure. Sure.  
**Parvesh Reddy:** Oh,  
**Sumit Malhotra:** So now we just simply when and one more thing that I updated is like previously when we are looking for the graphs from the data.  
   
 

### 00:16:55

   
**Sumit Malhotra:** So these are the static graphs that we are getting right.  
**Surya Pratap Singh:** Yeah.  
**Sumit Malhotra:** So now what will happen is I improved the graph structure also. Now the graphs are also interactive that we are creating after we run the analysis. So it will calculate the details what is mentioned. It will show this interactive graphs like how much large EVs, medium EVs and small EVs are there distribution by range it will be shown. Then based upon Mhm.  
**Surya Pratap Singh:** Uh, Sumit, I think uh last time I I spoke or I just texted in the chat box when we were doing uh Can you scroll up a little bit?  
**Sumit Malhotra:** Sure.  
**Parvesh Reddy:** Oh, instead of median to use mean.  
**Surya Pratap Singh:** Yeah. Yeah. Yeah. So, uh mean is basically not the real metric.  
**Sumit Malhotra:** Mhm.  
**Surya Pratap Singh:** So I think uh mean we can avoid using median will be rather good good term uh standard deviations actually these these are good for modeling purposes right and uh what what experimentalist look  
   
 

### 00:17:48

   
**Sumit Malhotra:** Okay. Mhm.  
**Surya Pratap Singh:** around is like uh for experimental people median is something that really existed right in the data set median always exists but mean is something uh it's a sometimes it becomes a misleading uh number right so  
**Sumit Malhotra:** Mhm. Okay. Okay. Got it. So basically what I'll do is I'll remove that main part. I'll stick to medium for all these purposes and I'll update that functionality here.  
**Surya Pratap Singh:** yeah yeah yeah yeah yeah uh I mean for maybe you can have a internal discussion uh pervacy what do you think like is that a meaningful number or basically they don't like actually mean number that's my observation  
**Sumit Malhotra:** Right. So this is the one thing that I will do that. Mhm. Okay.  
**Surya Pratap Singh:** yeah yeah because I I agree that mean and standard deviation for modeling purposes.  
**Parvesh Reddy:** Yeah, I agree because uh what we're looking at is separate buckets, right? So median will make more sense.  
**Sumit Malhotra:** No issues. Uh I'll I'll have a conversation with Praves regarding this and accordingly I'll update it whatsoever it is.  
   
 

### 00:19:13

   
**Surya Pratap Singh:** Those two numbers are very important. Uh median may not be very important but uh mean and median median and standard deviations are good. I mean essentially required whether you are applying normal distribution curve or anything. So uh I think uh uh for those purpose you can use these numbers. Uh but for but for display uh I think uh median itself will be sufficient.  
**Sumit Malhotra:** Mhm. Okay. Understood.  
**Surya Pratap Singh:** Uh yeah like that's my observation and u maybe we can have discussion and then we can finalize the things only bro here it is habitual people are habitual I'm calling sood too much  
**Sumit Malhotra:** Sure. Sure. Sure. Sure. Sorry. Sir. So apart from that no because ultimately you all are like from me.  
**Surya Pratap Singh:** yeah is good enough sura is good enough Yeah.  
**Sumit Malhotra:** Okay. So now apart from that what like previously when we are showing the graphs so these are all the static graph. So it is it doesn't have any functionality where we can zoom in or check the data in details or something like that.  
   
 

### 00:20:16

   
**Surya Pratap Singh:** Yeah. Yeah.  
**Sumit Malhotra:** So I updated that part as well. Every graph is now interactive where we can see any of the patterns any of the ranges in which specific range we can just simply zoom into the graphs and we can simply see all the details the number will shift accordingly.  
**Surya Pratap Singh:** Yes. Yes. Yes. Yeah.  
**Sumit Malhotra:** Apart from that there is one more thing that when I was uh reading the requirement file so one more thing I see that there is a cross comparison that we are that we need to do into the model. So I just try to create that functionality for now but it is it is not completely completed. So in this what it happen is when we let's say we do the flow cytometry uh experiment. Now here then we have a NTA data what right now if we upload any NTA file itself here.  
**Surya Pratap Singh:** Yes. Yes.  
**Sumit Malhotra:** So let's say this is one of the NTF files that we can use.  
   
 

### 00:21:11

   
**Sumit Malhotra:** So like whatsoever the data NTF file is showing this one is empty I believe. So it will be showing the data first of all in the NTA tab. Apart from that when we go to the cross comparison so we can here see the cross comparison between those both of these data from it will take data from both the tabs previously and show the data and inputs  
**Surya Pratap Singh:** Yes.  
**Sumit Malhotra:** here based upon both the files that we are compar comparing at the moment yes Sure.  
**Surya Pratap Singh:** Correct. Uh I think uh when I once I show then uh are you done sum? Okay. Uh can I show my screen for a time?  
**Sumit Malhotra:** Sure.  
**Surya Pratap Singh:** Yeah. Uh maybe uh once it is shared is it visible?  
**Abhishek Reddy:** So you can record the screen if you want.  
**Sumit Malhotra:** Uh yes, it is visible.  
**Surya Pratap Singh:** But something happened to my screen itself. Okay. Show my screen. Yeah. Uh okay.  
   
 

### 00:22:15

   
**Surya Pratap Singh:** So uh I was doing with uh NTA data FCS file only I was reading. Okay. I was going through FCS file only and uh they wanted to in a very limited range of data sets not all the possible you can see that right. So they wanted three categories. Initially uh there was a reason because they were uh using two filters. uh one was uh to cut off more bigger than 200 nanometer particles and the other was uh smaller than 50 nanometer particles and then they were arranging they wanted the total number of particles which were smaller than 50 nanometer and uh bigger than 200 and those which were falling in this range 200 50 to 200 nanometers. So something like this number they were interested and uh NTA uh maybe Pervesi might have some experience. Uh do you have any idea how NTA works?  
**Parvesh Reddy:** Um, no.  
**Surya Pratap Singh:** No. Okay. Okay. So basically uh NTA uh analyzes uh the Brownian motion of particles in the given solution and it uh captures randomly 11 frames and uh in each frame it captures some most probable particles and traces the it generates the trajectory it generates a video out of the brownier motion of each particle.  
   
 

### 00:24:00

   
**Surya Pratap Singh:** So like that say for example in an experiment this many total is somewhere 200 300 300 400 4003 451 particles were analyzed and these are the distribution of those 451 particles but this is not the actual number of particles. This is the particle which were actually analyzed and then based upon the uh analysis the overall number of particles they wanted to compute. So this is one anal analysis they wanted to have and the population of number of particles they wanted to have. So NDA generates two types of data.  
**Parvesh Reddy:** Surya G can you repeat that last bit before this?  
**Surya Pratap Singh:** One Yes.  
**Parvesh Reddy:** I missed that dynam.  
**Surya Pratap Singh:** Yes. Yeah. So basically uh NTA machine does what? It it analyzes it selects 11 11 frames uh and uh it uh it selects uh randomly some particles I mean most prominent and most uh uh like you know what Brownian visible is not  
**Parvesh Reddy:** Mhm.  
**Surya Pratap Singh:** very right. Brownian motion under Brownian motion those particles should be randomly moving in XY plane.  
   
 

### 00:25:21

   
**Surya Pratap Singh:** Okay. So most active particles you can say. Okay.  
**Parvesh Reddy:** Okay.  
**Surya Pratap Singh:** And uh it it sees the trajectory how uh like uh with how frequently they were changing their positions and uh based so once they start changing position a trajectory will be generated within few seconds it will record a video file of the trajectories and it just do the assemble like averaging of entire all the frames and calculates the like uh you know focus of view and And uh in the three-dimensional space it will convert that if if this this many particle in in a very limited range then how many particle in uh like 1 cm yeah 1 ml actually 1 ml volume how many particles could be so approximate number it generates it it usually falls in somewhere uh 100 million to few billions it can be like 10 ^ 7 order to uh sorry 10 ^ 7 to 10 ^ 10 order. It usually ranges usually that is the range of total number of nanop particles in the given 1 ml solution and uh the actual analysis is performed on only this many particles.  
   
 

### 00:26:30

   
**Parvesh Reddy:** Okay.  
**Surya Pratap Singh:** You can see somewhere around 3 400\. So based on that it it calculates the camera focus everything there the machine does calculations.  
**Parvesh Reddy:** Okay.  
**Surya Pratap Singh:** So uh machine does not allow us to read any raw file regarding how many particles are actually present in the solution. It does report only in a final output what is a PDF file. So you can see what I mean I was actually struggling for last many weeks so that I can uh see somewhere it is written in text file in FCS file actually it does not write anywhere. So uh from the FCS file or text file we can get only this information to compute I mean the simple thing was like this many particles are making 10 million particles. So only this fraction how many particles might be contributing. So just a ratio analysis we can do we can calculate the ratio times the total number of particles we can do. But that number is a difficult uh question I was struggling through.  
   
 

### 00:27:51

   
**Surya Pratap Singh:** So yesterday I was uh I mean sorry finally I was able to last week uh I was able to decide okay let's start reading PDF file only and uh I did not have much solution how to read PDF file in uh so I use this library pi PDF2 and uh I was uh analyze getting that uh you know that number because that number is not not ever mentioned in a text format. it is always mentioned only in the PDF file. So uh and later I wanted uh I got this this graph.  
**Parvesh Reddy:** Copy.  
**Surya Pratap Singh:** I mean this is the second thing they want. So they ultimately will be required requiring for what is the total population of particles in the range wise and what was the actually analyzed particle in the camera focus. So these two will be the things they will ask. Am I clear until this point now?  
**Parvesh Reddy:** Yeah. Can you give us one of these PDF files?  
**Surya Pratap Singh:** Yeah, that is what I was I was about to come.  
   
 

### 00:28:59

   
**Surya Pratap Singh:** So, uh I will uh I was about to ask that uh I I'll close the presentation.  
**Parvesh Reddy:** No, no, we can still see the  
**Surya Pratap Singh:** Okay. Okay. So uh like uh uh what I can see what I was planning like I shall share uh FCS file along with the uh PDFs. So uh and I can help actually the there is a line regular expression. Yes, please hang on section. Yeah. So I was I was looking for the line original concentration. Okay. So there will be I I'll okay please uh I'll I'll show you maybe yeah I think I shared that  
**Parvesh Reddy:** We are still seeing only BS code.  
**Surya Pratap Singh:** tab not is Actually this is the second what you call second screen is it visible.  
**Parvesh Reddy:** Okay. Yeah.  
**Surya Pratap Singh:** Can you see that?  
**Parvesh Reddy:** Yeah. Yeah. Can Can you zoom in a little bit?  
**Surya Pratap Singh:** Just a second please. So is it is it readable?  
   
 

### 00:30:31

   
**Parvesh Reddy:** Yeah. Yeah. Yeah.  
**Surya Pratap Singh:** So basically here yeah you can see even here they are mentioning uh medians and standard. Anyway this is not useful term what we are talking about. So actually actual analysis is this one. this many particles per ml they are able to see is it readable to you what time okay so sorry yeah and then dilution factor is so this sample was diluted for uh 500 times and this  
**Parvesh Reddy:** Yeah. Yeah. No. No. We can do Candy.  
**Surya Pratap Singh:** is the entry users will made we user will make okay so simply this number multiplied to the calcul calculated concentration like 500 times. So this number will convert into 3 into 10 ^ 3.5 into 10^ 10 particles per ml. So the original concentration is nothing but this multiplied by this. However, uh since we are going to calculate the possible particle concentration, this is a meaningless number for us. We will we can get the numbers from here itself.  
   
 

### 00:31:55

   
**Surya Pratap Singh:** So I I was fetching I I was actually trying to fet find out this number but I was unable to get anywhere.  
**Parvesh Reddy:** Um I have a question now. The text file has concentrations uh for each particle size right in the table.  
**Surya Pratap Singh:** Uh Okay.  
**Parvesh Reddy:** Can we not add up all those concentrations and then multiply it by the dilution factor?  
**Surya Pratap Singh:** Uh, I think I need to look at uh maybe I'll I'll check around and Yeah. If that works, maybe that point I missed. Yeah. Okay. then it it solves all the problem right even I'm not sure uh let me see let me see let me see  
**Parvesh Reddy:** Yeah, but I I don't know if that is taken separately like that.  
**Surya Pratap Singh:** so concentration No, I don't think that will work. I don't think that will work, sir.  
**Parvesh Reddy:** Okay.  
**Surya Pratap Singh:** Because these are somewhere uh actually these are per frame concentrations. You see their numbers if you have yeah but uh like okay maybe this file is very old and uh incorrect way of it was done.  
   
 

### 00:33:49

   
**Parvesh Reddy:** Per cubic cm, right?  
**Surya Pratap Singh:** Okay, I will do what one thing I'll uh analyze with one recently done file and with the same experiment what I had calculated for uh text file of the same experiment and I'll compare the result and then I'll come back I'll write an email just today itself I'll I'll do that and I'll I'll uh write that.  
**Parvesh Reddy:** Okay. Okay. Sure. No problem.  
**Surya Pratap Singh:** Yeah. Anything else?  
**Parvesh Reddy:** Um I am I don't have any other updates.  
**Sumit Malhotra:** Uh, no, not from my side.  
**Parvesh Reddy:** Charming.  
**Surya Pratap Singh:** Okay. So, yeah, I'll close this.  
**Parvesh Reddy:** Yeah, I think we're good from our end. Abishek, do you have anything you want to add?  
**Abhishek Reddy:** No, no, no. Pretty much I covered him.  
**Surya Pratap Singh:** Okay.  
**Parvesh Reddy:** Okay.  
**Surya Pratap Singh:** Okay. So what I'll do like uh uh I'll try to check with the text file if it works then our problem is mostly solved uh because unnecessarily uh I did not want to read that PDF file but since we don't have that uh I mean if if there is no option we will be ending up with the PDF file reading only that will be the only thing we can do I'll I'll share I'll share I'll share uh  
**Parvesh Reddy:** Yeah. So, in the meantime, you can give us one or two of those PDF files. We'll still look at it and see if we can parse it.  
**Surya Pratap Singh:** just uh half an hour I'll share today itself because there are lot of good data sets actually the guy Somukha he is actually in a meeting I was expecting him around 3:00 so he's still in meeting so once  
**Parvesh Reddy:** Okay.  
**Surya Pratap Singh:** he is done I'll ask him I mean he has shared but I wanted to ask him like which files you want to share you want me to share so once he approves I will share the things  
**Parvesh Reddy:** Okay. Yeah. Um, no. Very good. Yeah. Yeah.  
**Abhishek Reddy:** Yes.  
**Parvesh Reddy:** Thank you.  
**Abhishek Reddy:** Thank you.  
**Parvesh Reddy:** Thank you.  
**Abhishek Reddy:** Thank you, S. Yeah. You want to stop  
   
 

### Transcription ended after 00:36:14

*This editable transcript was computer generated and might contain errors. People can also change the text after it was created.*

Nov 27, 2025

## Biovaram Weekly Customer Connect.  \- Transcript

### 00:00:00

   
**Parvesh Reddy:** Hello. Hi, Simon. Okay. Okay. Need to check if I can record this. Okay. How you feeling now, S?  
**Sumit Malhotra:** are better.  
**Parvesh Reddy:** See is also working from home.  
**Sumit Malhotra:** So like what are we going to exactly discuss today?  
**Parvesh Reddy:** Um nothing today just mention what um the postgrad is optimizing.  
**Sumit Malhotra:** Mhm. I I did one more thing. I'll show you right away.  
**Parvesh Reddy:** Yeah. So we can just show them these and then I believe um our MD should be meeting them soon. Once they have met, I think we can uh start using the AI cuz I think they'll give us credentials or whatever.  
**Sumit Malhotra:** Mhm.  
**Parvesh Reddy:** At that point, we can integrate both of these systems, start doing the training, request what kind of uh training data we need, all that stuff.  
**Sumit Malhotra:** Mhm. Mhm. I connected my back end with the UI that Mohit sent me a little bit some functionality not the complete back end and and tested this.  
   
 

### 00:05:56

   
**Sumit Malhotra:** So it is working good here like all the analysis and everything is working smoothly and fastly  
**Parvesh Reddy:** Okay, is here. Um hello. Hi.  
**Surya Pratap Singh:** Hello everyone.  
**Parvesh Reddy:** Will U Jagans sir also join us?  
**Surya Pratap Singh:** Actually, I could not meet him and I'm not sure.  
**Parvesh Reddy:** Okay. Because yesterday evening I believe he had spoken to Abishek and said he wanted to have the meeting today. So that's why  
**Abhishek Reddy:** Yeah.  
**Surya Pratap Singh:** Okay, then he will definitely join.  
**Abhishek Reddy:** Hi Surya.  
**Surya Pratap Singh:** Hi MC.  
**Abhishek Reddy:** Yeah, Jagen wanted to connect today. So that's the it. reason we scheduled No, that's fine too.  
**Surya Pratap Singh:** Yeah. Yeah. Yeah. Actually, sorry for yesterday's uh glitch. I totally forgot that uh that it was a recurrent meeting and uh at the time Pervesi texted me.  
**Abhishek Reddy:** Yeah.  
**Surya Pratap Singh:** That time I was actually with my friend and I was in not a situation to join the meeting unfortunately.  
   
 

### 00:07:18

   
**Surya Pratap Singh:** He might join very soon. Hello. Hello G. Yeah.  
**Parvesh Reddy:** Yeah.  
**Abhishek Reddy:** That's Yeah.  
**Surya Pratap Singh:** Uh do Yeah. Uh do you have plan to visit uh Hyderabad? I mean visiting here.  
**Abhishek Reddy:** Nothing is planned as of now. Yeah.  
**Surya Pratap Singh:** Okay. Actually yesterday Vikrans was asking that uh uh are they coming sometime soon? I had no clue.  
**Abhishek Reddy:** No, I think Vinod and Vishal were expected to come today but due to some some change in plan I think they're not uh they were not joined.  
**Parvesh Reddy:** Ow.  
**Surya Pratap Singh:** Uh yeah.  
**Abhishek Reddy:** Actually they were supposed to be meet today.  
**Surya Pratap Singh:** So he has Yeah.  
**Abhishek Reddy:** They had some change in plan. Yeah. Hi.  
**Parvesh Reddy:** No, you're on mute.  
**jaganmohan reddy:** Uh, hi Pervish. Hi. How are you?  
**Abhishek Reddy:** Hi. Hi. Yeah. Yeah. Good. Thank you. How you s Yeah.  
   
 

### 00:09:43

   
**jaganmohan reddy:** I'm fine. I'm fine. Yeah, please go ahead. Here.  
**Parvesh Reddy:** Okay. Um can we start with the UI first and um Mo can you share your screen or Sum whoever.  
**Sumit Malhotra:** Uh I will do that if it is okay. So here's the UI.  
**Parvesh Reddy:** So we'll start one second.  
**Charmi Dholakia:** Hi everyone.  
**jaganmohan reddy:** How you doing?  
**Parvesh Reddy:** Yeah. So, we've uh updated the UI. Uh it's a little more uh flashy and at the same time we've added a new tab called nanop particle tracking where um we can add the NTA data. Can you click on that S?  
**Sumit Malhotra:** Yeah. Yeah.  
**Parvesh Reddy:** Uh yeah. So, here we can add the NTA uh files.  
**jaganmohan reddy:** Hey,  
**Parvesh Reddy:** And if we go down once we add one of the files, we'll be able to see the uh best practices uh pop up.  
**Sumit Malhotra:** Just like this. Like we see here  
**Parvesh Reddy:** Yeah. And u we are planning to add a functionality where the charts that are populated in the bottom here we can pin to the dashboard in the first page.  
   
 

### 00:11:07

   
**Parvesh Reddy:** So people can add the files here. uh once they're happy with certain graphs, they can add it to the first page and they can do their analysis there in that page.  
**jaganmohan reddy:** Okay.  
**Parvesh Reddy:** Uh apart from that, we've added a few cards here.  
**Sumit Malhotra:** Thank you.  
**Parvesh Reddy:** Here we're not particularly sure what exactly to show on top as like the main highlights for from the data.  
**jaganmohan reddy:** Yeah.  
**Parvesh Reddy:** Uh I was thinking maybe we can show like uh the section. How many particles are there in each uh uh size range? Maybe between 40 and 80\. How many particles? Between 80 and uh 100 how many particles? Something like that.  
**jaganmohan reddy:** Yeah.  
**Parvesh Reddy:** Um, if you can give us some guidance on what you would like to see up here on these uh four uh cards, it'll be helpful.  
**jaganmohan reddy:** Yeah. Yeah. So this one uh generally there are different ways to analyze this uh different ways to categorize this one. So 30 to 100 are generally called as small recules and that is one categorization.  
   
 

### 00:12:22

   
**jaganmohan reddy:** Okay. And 30 to 150 is another categorization of Us.  
**Parvesh Reddy:** Okay.  
**jaganmohan reddy:** Okay. So what we can do is Yeah.  
**Parvesh Reddy:** So here we are seeing particles from uh 40 to 180\. Okay.  
**jaganmohan reddy:** So what the better way to project this is give them the choice to okay what is the range that you want to select. So, so they they get the choice. Okay. Select between uh to count the total between 30 to 150\. We should get the total count and uh the details of those ones, right?  
**Parvesh Reddy:** Okay.  
**jaganmohan reddy:** Uh so that would be the better so that they will they will have the freedom to operate. We will not be the persons who judge on that one.  
**Parvesh Reddy:** Okay.  
**jaganmohan reddy:** So they they will always have the option to choose. So if I were depending upon my application suppose say if I want to identify small vicles uh between 30 to 100 as one segment and 100 to 150 as another segment I would do that because for various reasons  
   
 

### 00:13:28

   
**Parvesh Reddy:** Okay, sure.  
**jaganmohan reddy:** in scientific uh applications and scientific thought process right yeah that is one thing yeah this is the NDA data Right.  
**Parvesh Reddy:** We'll implement that. Uh yeah. So here we'll be pin we can we'll have an functionality where we can select one of these graphs and pin it to the first page.  
**Surya Pratap Singh:** This is not NTA data. I think  
**Sumit Malhotra:** This is the fax data manifax.  
**Parvesh Reddy:** The psycho psychometric data  
**jaganmohan reddy:** Yeah. Because that's how I see. Okay. Uh please don't mind my cough and uh cold. Yeah. So yeah this is a in cytometry data. So in this there are several factors in this. If you go above like what uh previously so still uh yeah so here you are getting VSSC 1A measured ratio estimated diameter right this is yeah  
**Parvesh Reddy:** Correct. So this measure the estimated diameter we are calculating using the MI thing.  
**jaganmohan reddy:** yeah I got it I got it. uh so there will be various parameters in the nanoflex that need to be analyzed and also we should show them.  
   
 

### 00:14:52

   
**jaganmohan reddy:** This is the tricky part and this is the most uh exciting part at the same time for me. Okay.  
**Sumit Malhotra:** Yeah. So, uh just to add on here, uh from here you can actually select all the parameters that you want to calculate or go through and based upon the selection like I made the selection of violet forward skater height  
**jaganmohan reddy:** Mhm.  
**Sumit Malhotra:** and violet side scatter one area. So that is why it is showing these two fields here and the analysis part.  
**jaganmohan reddy:** Yeah.  
**Sumit Malhotra:** But we can completely choose any of the fields or any of the ranges that we need to do that analysis part.  
**jaganmohan reddy:** Yeah. Yeah. This will become more manual. What happens is sometimes when you have majority of the things that you are analyzing in that because there are several parameters, right? So sometimes users would not look into the other parameters that it is affecting. So one of the thought process while doing this one was do we find ourself a distinguish factor out of various of those combinations like okay we can report to the user okay bar these are all your parameters but see it seems like uh you are getting some anomaly here like look into this kind of thing Yeah.  
   
 

### 00:16:07

   
**Parvesh Reddy:** Huh? For that actually we need to use the AI. Right now we still haven't gotten uh access to the AI the data cloud and AI yet. So what we're doing right now is all u coding alone.  
**jaganmohan reddy:** Yeah. Yeah. Yeah. So that is that is something that uh I want like you to keep in mind for future let know like just to keep there in track.  
**Parvesh Reddy:** But can you give us like a list of um the graphs that we should be looking at or at least what the AI should be looking at? like uh rather than have it check all of the parameters, is there like a specific maybe uh I know head height versus area.  
**jaganmohan reddy:** Yeah, yeah, I'll do that part. I'll do that part. Actually, probably we'll sit down and uh write down those points how to get those things right. Okay.  
**Parvesh Reddy:** Yeah. And then we can use the AI to check those specific graphs, all of those graphs, check the anomalies in those graphs and show it back to the u user.  
   
 

### 00:17:09

   
**jaganmohan reddy:** Yeah. Yeah. So, yeah. So, right now they are establishing various protocols right now know probably it might take another two weeks. So, I'll get that data and probably once that data is done then we can put that data and then show how to do that. We will do that part. Yeah.  
**Parvesh Reddy:** Okay.  
**jaganmohan reddy:** Yeah. Yeah. So far it looks good.  
**Parvesh Reddy:** Yeah. So for now while we're waiting on that data we will start um we'll start doing back backend optimization and along with that uh if once we have access to the AI we'll start training the data uh the AI  
**jaganmohan reddy:** Yeah.  
**Parvesh Reddy:** for the NTA data um Yeah.  
**jaganmohan reddy:** Yeah. Mhm. uh probably sometime in the next week or so I'll sit down and go through the data that sur has given you and probably we might find a way to put this here okay even for so let's yeah  
**Surya Pratap Singh:** uh Jagen sir. Yeah. Uh like uh recent data I have not given.  
   
 

### 00:18:24

   
**Surya Pratap Singh:** Uh all old data only I have given.  
**jaganmohan reddy:** Okay.  
**Surya Pratap Singh:** So uh recent data I am internally analyzing.  
**jaganmohan reddy:** Okay.  
**Surya Pratap Singh:** uh and uh I whatever you are see maybe Sumuka might have shown you some data for last couple of weeks data those are internally only analyzed I did not share with them okay  
**jaganmohan reddy:** Okay. Actually last week and this week I did not sit with anybody. Probably tomorrow I sit with all the people. So I would know.  
**Surya Pratap Singh:** Okay.  
**jaganmohan reddy:** Yeah. Okay. Okay. Yeah.  
**Parvesh Reddy:** Yeah.  
**jaganmohan reddy:** Yeah.  
**Parvesh Reddy:** So that's what we have for now. Um Abishek, do you know when uh the meeting with uh um Vinodar is rescheduled to or Okay.  
**Abhishek Reddy:** No, they were supposed to they're supposed to go today, but due to some challenge, they could not make it.  
**jaganmohan reddy:** Yeah.  
**Abhishek Reddy:** Yeah. I'm not sure when they're going to go back.  
**jaganmohan reddy:** Yeah. And it will be on third. Let's see that.  
   
 

### 00:19:26

   
**jaganmohan reddy:** It's It's fine.  
**Parvesh Reddy:** Okay. Do we need to send the s or no?  
**Abhishek Reddy:** Yeah. No, I think I've already shared with Vinod. I think he'll take it up with Jagans. Yeah.  
**jaganmohan reddy:** Yeah.  
**Parvesh Reddy:** Okay.  
**jaganmohan reddy:** Yeah. Okay.  
**Charmi Dholakia:** I wanted to ask one thing.  
**jaganmohan reddy:** Yeah. You start 4 in the afternoon.  
**Charmi Dholakia:** Instead of 750, can we keep it at 4 uh from next week?  
**Abhishek Reddy:** You're going to 4 p.m.  
**Charmi Dholakia:** 4\. Yeah. 4 or 3:30 or 4\. Yeah.  
**Abhishek Reddy:** Which day is preferred? Like uh Mhm.  
**Charmi Dholakia:** Thursday is fine. Yeah. Thursday 3:30 4:00.  
**Surya Pratap Singh:** Yeah, for me it is okay. Anything is okay. I'm sorry. Yesterday one I completely actually in the beginning we were talking about on Thursdays and last week it happened on Wednesday and yesterday I completely skipped that.  
**Abhishek Reddy:** Yeah.  
**Surya Pratap Singh:** Uh uh it is Yeah.  
**Abhishek Reddy:** No, we'll just keep it to Thursday every every week.  
   
 

### 00:20:22

   
**Parvesh Reddy:** Yeah.  
**Surya Pratap Singh:** Yeah.  
**Abhishek Reddy:** Yes, sir.  
**Surya Pratap Singh:** Actually, initially it was on Thursdays only. Uh last week only it happened on Wednesday and since then so I completely skipped I mean completely forgot that uh today there will be  
**Abhishek Reddy:** Yeah. Okay. Yeah. No, not an not an issue. Sorry.  
**jaganmohan reddy:** Okay, sounds good. Let's see. Uh, irrespective of me, you can carry as long as Surya is involved.  
**Abhishek Reddy:** Yeah.  
**jaganmohan reddy:** So, because sometimes my schedules are like, you know, very it it goes there day by day.  
**Abhishek Reddy:** Yeah. Good.  
**jaganmohan reddy:** So yeah, we will see. Yeah.  
**Abhishek Reddy:** Yeah. Yeah. Sure.  
**Parvesh Reddy:** So it'll be Thursdays 4:30 to 5:30 is it?  
**jaganmohan reddy:** Yeah.  
**Parvesh Reddy:** Okay.  
**Charmi Dholakia:** Uh no no 3:30 before 5 any time.  
**Parvesh Reddy:** Before five I have Ignite.  
**Charmi Dholakia:** Yeah. So 3:30 to 4:30 or 4 to 5\. Yeah.  
**Parvesh Reddy:** Uh, Thursday might not be possible for me. Um, is witness day. Okay.  
**Charmi Dholakia:** Wednesday is also okay.  
**Parvesh Reddy:** Okay. So then I I'll have it I'll put it at Vness day uh 4 to 5\. Okay.  
**Charmi Dholakia:** Yeah. 4 to 5 is fine. Yes.  
**Surya Pratap Singh:** Okay, for me it is okay.  
**jaganmohan reddy:** Okay.  
**Parvesh Reddy:** Yeah, I'll keep it recurring. Um if if there's some changes we can reschedu Okay.  
**jaganmohan reddy:** Yeah, sounds good. Sounds good. Yeah.  
**Parvesh Reddy:** Yeah.  
**jaganmohan reddy:** Yeah.  
**Parvesh Reddy:** Thank you.  
**Charmi Dholakia:** Thank Thank you.  
**jaganmohan reddy:** Thank you all.  
**Abhishek Reddy:** Thank you. Thank you.  
**Sumit Malhotra:** Everybody.  
**Abhishek Reddy:** Thank you.  
**Parvesh Reddy:** Okay.  
**Sumit Malhotra:** and uh Moit and Pravesh. Uh so basically what I was showing you previously before joining Sury and Jagans uh yes  
**Parvesh Reddy:** Uh one second. Let me stop the  
**Abhishek Reddy:** Yeah, you can stop the recording question.  
   
 

### Transcription ended after 00:22:12

*This editable transcript was computer generated and might contain errors. People can also change the text after it was created.*

Nov 19, 2025

## Biovaram Weekly Customer Connect.  \- Transcript

### 00:00:00

   
**Sumit Malhotra:** Hi guys, how are you?  
**Parvesh Reddy:** I see.  
**Sumit Malhotra:** How are you? Parvesh  just suffering from cold.  
**Abhishek Reddy:** Good summit. How are you? Cold weather, I think.  
**Sumit Malhotra:** Yeah, some some folks suffering in North India.  
**Parvesh Reddy:** One second.  
**Abhishek Reddy:** Yeah.  
**Parvesh Reddy:** Oh, now I can hear. Sorry, I missed I missed the beginning. Can you guys repeat?  
**Sumit Malhotra:** I'm just asking how are you  
**Abhishek Reddy:** How are you?  
**Parvesh Reddy:** Okay. Yeah, we'll just wait for the others to join.  
**Abhishek Reddy:** Don't forget to record.  
**Parvesh Reddy:** Yeah, I'll put it.  
**Sumit Malhotra:** In the meantime, Pvish, I I check the UI that Moit sent me.  
**Parvesh Reddy:** Yeah. Okay.  
**Sumit Malhotra:** So in that like whatever the functions Mo is currently using and if we goes upon that specific functions. So uh the the app should be the app would be very slow. So I optimized it further the batch processing and everything I created a plan for that to optimize it. So within the next week what we can do is uh we can just simply connect the UI that we have at the moment with the uh the back end with the optimized back end and we should be able to produce some of the data that will be live data coming into the streams.  
   
 

### 00:06:55

   
**Parvesh Reddy:** What mentioned that you wanted to switch from streamlet to React?  
**Sumit Malhotra:** I mentioned it like basically not specifically switching. I just suggested that with the react like we can create a like it is totally based upon design purposes like in the react we have many good libraries we can use and important and it can help us to get a better looking UI nothing else.  
**Parvesh Reddy:** Yeah. So we can we can try it out and see what um Sure.  
**Sumit Malhotra:** Sure. Then uh I'll I'll create a plan for that and I uh show you that as well.  
**Parvesh Reddy:** I asked Mo to look into it. So he said he will um so he So he said he'll give it a shot and try to convert what we currently have into.  
**Sumit Malhotra:** Mhm.  
**Abhishek Reddy:** Hi. Sorry.  
**Surya Pratap Singh:** CF60 is  
**Abhishek Reddy:** Good evening.  
**Sumit Malhotra:** I I I'll I'll uh connect with Mo tomorrow and I'll help him out with the React part. I'll let him know that how he can create prototype or samples in React faster and reliable.  
   
 

### 00:08:07

   
**Sumit Malhotra:** So I'll help him with that part.  
**Parvesh Reddy:** Okay. Um so Mo can you share the UI that we have now?  
**Surya Pratap Singh:** uh for seat uh uh I have a uh like a problem at my end that a network issue is there so I'm sharing someone else's space okay uh so like uh this is the only thing like if something  
**Parvesh Reddy:** Yes. Okay.  
**Surya Pratap Singh:** happens uh I mean consider that I'm unable to rejoin right yeah I'm not sure uh because at his end uh uh the internet is very bad actually he's in lipic and hotel internet is extremely bad  
**Abhishek Reddy:** Okay.  
**Parvesh Reddy:** Okay, that's no problem.  
**Abhishek Reddy:** Okay. Will Tan also be joining? Okay. Okay. Mhm. Okay. Okay.  
**Parvesh Reddy:** Okay, we'll try to keep uh today's update quick and brief.  
**Surya Pratap Singh:** Yeah. Yeah.  
**Parvesh Reddy:** Um we have uh me uh we put together a cost estimate for uh uh AWS and um and um clawed together.  
**Surya Pratap Singh:** Yeah. Yeah.  
   
 

### 00:09:20

   
**Parvesh Reddy:** Uh so we have that in two separate files actually.  
**Surya Pratap Singh:** Mhm.  
**Parvesh Reddy:** So what I'll do is since we can't present it right now, I'll send it across by email. That might be better.  
**Surya Pratap Singh:** Yeah. Yeah, that will better actually.  
**Parvesh Reddy:** Yeah. So I'll I'll share that across by email and um right now we'll keep our updates brief. Um apart from a little bit of optimization and UI changes, we haven't uh uh pushed through too much.  
**Surya Pratap Singh:** Yeah, that's and uh at my end as we had a telephonic conversation yesterday, I told the team to generate data with a proper nomenclature.  
**Parvesh Reddy:** So we I'll just show quickly show you uh more. Can you show the UI?  
**Surya Pratap Singh:** Say for example if experiment A is going on so file name should be A and there will be some variables like uh methodology related. So the file name will be consistent for NTA and F uh nanofax.  
**Parvesh Reddy:** Okay.  
**Surya Pratap Singh:** So that that that is what you were expecting right?  
   
 

### 00:10:25

   
**Parvesh Reddy:** Yeah.  
**Surya Pratap Singh:** Yeah. So, so, so you know what is uh like rel related file, which files are related, which files are not related, right?  
**Parvesh Reddy:** Yeah.  
**Surya Pratap Singh:** So, I have I have discussed with them today and uh they said that they will they will from now onwards they will share me data in that context that uh way only.  
**Parvesh Reddy:** Apart from that, I believe Sumit had a few questions to ask.  
**Surya Pratap Singh:** Yeah. Yeah. Please, please. Uh yeah.  
**Sumit Malhotra:** Uh yes sura. So basically my question sure sure  
**Parvesh Reddy:** But before we start, let's just quickly show off the UI and then we can start the question.  
**Mohith M:** Is my screen visible?  
**Parvesh Reddy:** Yeah, your screen is visible. Yeah. So, right now we have the uh EV analysis tool. We got the logo put on the side rather than have a long name.  
**Surya Pratap Singh:** Uhhuh. Yeah. Yeah.  
**Parvesh Reddy:** The sidebar still exists.  
**Surya Pratap Singh:** Yes.  
   
 

### 00:11:22

   
**Parvesh Reddy:** Um what we've added to the sidebar. One second. Sorry. Sorry. Um so what we've added to the sidebar is um for the calculations of size we have a few parameters that we've added to the sidebar so that we can uh change it based on the thing where so for  
**Surya Pratap Singh:** Yeah.  
**Parvesh Reddy:** example if we using a different wavelength for the FCS data we can change that here for the particle for the exosomes refractive index we can change that as well.  
**Surya Pratap Singh:** Ah, correct. Correct. Correct. Yes. Yes.  
**Parvesh Reddy:** uh the substrate that you're using if you use a different substrate that can be changed. Uh FCS angle the scattering angle for forward direction that can be varied for the side angle also that can be varied.  
**Surya Pratap Singh:** Yes. Yeah.  
**Parvesh Reddy:** And if we're looking for like a specific size range, we can change that also.  
**Surya Pratap Singh:** Yeah. I have a small query. I I mean is it random uh scatter plot or you have uh calculated some values there?  
   
 

### 00:12:29

   
**Parvesh Reddy:** Mhm.  
**Surya Pratap Singh:** Here I see some are random.  
**Parvesh Reddy:** This is just a random scatter plot. But on the other the next tab where it says particle size analysis, the calculation will actually happen.  
**Surya Pratap Singh:** Okay. Yeah.  
**Parvesh Reddy:** But quickly I'll just show you the rest of the uh sidebar. Um yeah so diameter points resolution is simply how many uh values we're planning to take between 40 and 180\. Uh and there's a few other settings that uh we can decide on but these are not these just be  
**Surya Pratap Singh:** Yeah.  
**Parvesh Reddy:** for now we've put these settings where u the values that are minus on the side and forward scatter will get neglected and it's zero again that also will get neglected.  
**Surya Pratap Singh:** H. Okay.  
**Parvesh Reddy:** So this is this is what we made. Mo, can you just add a random FCS file? One of the files that we have. Yeah. So, uh we what is happening in the background is these files are getting converted to parket format to reduce the file size and u the uploaded data.  
   
 

### 00:13:44

   
**Surya Pratap Singh:** Yes. Yes. Yes.  
**Parvesh Reddy:** You can see the whole uh  
**Surya Pratap Singh:** Yeah. That is actually not necessary. Uh as as last time either Moit or Sumit some of the guy who mentioned this thing. I think Sumit only mentioned to use pocket size right so that's better idea actually unnecessarily filling the memory is not a great idea hi Charlie so  
**Parvesh Reddy:** Yeah.  
**Charmi Dholakia:** I'm a little Yeah, sorry. I'm a little late today. Five minutes late.  
**Parvesh Reddy:** Yeah, it's fine. Uh so yeah so along with this we can um decide on which of the columns we need to use that is our no no what's happening here is to decide  
**Surya Pratap Singh:** yeah rather parameter selection is a better option and then that time When we select the two parameters full of those two uh data should be loaded right now.  
**Parvesh Reddy:** which two uh columns to use to calculate the size so we can Um here we weren't too sure if uh you want to later use like uh the colored scattering the colored side scatters for calculating size.  
   
 

### 00:14:46

   
**Surya Pratap Singh:** Okay.  
**Parvesh Reddy:** So we put all of the columns but I remember we had a conversation once that to use only forward scatter and uh violet side scatter one or two to decide on the size but I I wasn't too sure  
**Surya Pratap Singh:** Okay. Actually uh if you remember uh like even in the paper what we had seen the uh half angle scattering side scatter is the better parameter.  
**Parvesh Reddy:** what the conversation fully was. Mhm.  
**Surya Pratap Singh:** So just uh if I can if if you can log to the drive I think how did I share the paper drive only right?  
**Parvesh Reddy:** Uh, it's on the drive. Yeah.  
**Surya Pratap Singh:** Uh just stay there like I have a request like uh uh can I add that drive to my Gmail drive that way it will be difficult actually uh because I'm  
**Parvesh Reddy:** Yeah, you can uh save a shortcut.  
**Surya Pratap Singh:** not uh carrying the same laptop everywhere like office has different machine and home has different Yeah.  
**Parvesh Reddy:** No, no, no. As in like to your uh drive, you can put a shortcut to this drive.  
   
 

### 00:16:17

   
**Surya Pratap Singh:** Okay. Okay. I'll try to fix that issue. Uh but right now I'll search cuz every time I I did not actually try to add try.  
**Parvesh Reddy:** So here we're selecting forward scatter and one side scatter one. If we run the analysis you'll see that uh it'll generate a few plots and sizes.  
**Surya Pratap Singh:** Yeah. Yeah. Uh yeah that I understand like uh you are doing one forward scatter and one side scatter one will be both are in the height side right.  
**Parvesh Reddy:** Yeah, not to generate a graph.  
**Surya Pratap Singh:** Yeah that is so you will you will you will generate a a graph that is that is the each particle.  
**Parvesh Reddy:** This is to actually generate the sizes of each uh yeah.  
**Surya Pratap Singh:** Okay. Okay. Okay.  
**Parvesh Reddy:** So here this that the question we had was do we use I know we like from the paper the bessel function paper it says we need to use one forward scatter one side scatter but we're not sure which  
   
 

### 00:17:23

   
**Surya Pratap Singh:** Uh-huh.  
**Parvesh Reddy:** side scatter to use because here we're using V SSC1 but we could easily use SSC 2 or the B SSC's or the Y SSSE there's a lot of parameters so we could use any of So that we wanted  
**Surya Pratap Singh:** Yeah. Yes.  
**Parvesh Reddy:** clarification from you which one to use for uh the vessel functions to calculate the size.  
**Surya Pratap Singh:** Okay. Uh, actually I'll I'll I'll just hold a minute. Uh I'll I'll try to log in and 75 what actually happens. Yeah. Yeah. So uh our EVs uh like exosomes that uh why we are using VSSSC right that is your concern why we are not using other SSCs right?  
**Parvesh Reddy:** Correct.  
**Surya Pratap Singh:** Yeah. So basically uh most of the uh like uh time uh okay let me load that web. I mean I can I share my screen that you have to turn down right opening a new tab.  
**Parvesh Reddy:** Yeah.  
**Mohith M:** s\*\*\*.  
**Surya Pratap Singh:** Yeah.  
   
 

### 00:19:19

   
**Surya Pratap Singh:** Uh share. So is it visible now? Yeah. So this paper we are referring right actually this is the paper where where they have shown to how to convert right like this paper describe all the methods.  
**Parvesh Reddy:** Correct.  
**Surya Pratap Singh:** So here yeah uh I think that uh we need to consider something here. So if you see very small uh size particle right like uh like when when the cross-section of scattering is very small in that case you see it's almost uh there is no change right uh we uh we are unable to see any changes but like when this there is a some some sort of like a 10-fold increase then we can see some changes and uh when the scattering cross-section is significantly high like almost billion order high right 10 ^ \- 10 order rather 10 ^ \- 9 order you can see the significant uh changes at the same wavelength and this wavelength 488 Uh we see the outputs in the green channel. Sorry.  
   
 

### 00:21:00

   
**Surya Pratap Singh:** Uh if I Okay. So is it like you got this point?  
**Parvesh Reddy:** So we see it in the green channel. Is it Mhm.  
**Surya Pratap Singh:** Yeah. Like yeah we see this in the green channel but the excitement of the dye that happen like so uh I think uh pervis you can understand this point. So any fluoro we have two things. one is excite like excitation lambda max and emission lambda max.  
**Parvesh Reddy:** Correct. Correct.  
**Surya Pratap Singh:** So the excitations are somewhere far ahead of emission right uh which are usually uh somewhere for for this 488 uh plural force like mostly it will be somewhere in the uh blue or violet range like somewhere  
**Parvesh Reddy:** Okay.  
**Surya Pratap Singh:** 405 or something like that.  
**Parvesh Reddy:** Okay.  
**Surya Pratap Singh:** So the like most of the biology like most of the time you will see either they are seeing the things in green and red. Actually there is no set rule but mostly this is how they are seeing the like biological samples red and green channels and there most of the excitation lambda maxes are in the blue or violet range.  
   
 

### 00:22:20

   
**Surya Pratap Singh:** So here whatever like and and uh uh okay I'll I'll close this one stop sharing right. So uh uh when we do this uh uh like a blue and violet we expect that uh you know like their uh shorter wavelengths will have more uh intensities to like you know like then we see more uh like post scattering we'll see more uh you know scattering lambda max we will see you got am Am I clear or I'm bit confused?  
**Parvesh Reddy:** Okay. Little bit confused.  
**Surya Pratap Singh:** Okay.  
**Parvesh Reddy:** Could you Mhm.  
**Surya Pratap Singh:** Uh yeah like uh because last I I understand that where I I made the things messy. See longer wavelengths like yellow and red uh their scattering uh like when when they do scatter like when they do do hit on the particle and then uh whether it is forward scatter or side scatter their effect will be minimal as compared to the high intensity wavelengths.  
**Parvesh Reddy:** Violet lasers.  
**Surya Pratap Singh:** Right? So that is why mostly people choose the lower wavelength uh lasers.  
   
 

### 00:23:44

   
**Surya Pratap Singh:** So these are right yes uh forward uh for modeling I think uh side scatter will be important right?  
**Parvesh Reddy:** Okay. Okay. So that's why we'll be using either V uh SSC 1 or SSC 2\. and forward scattering, right? No, but for the vessel functions, we're supposed to use Yeah.  
**Surya Pratap Singh:** Ah, correct correct correct correct. Yeah.  
**Parvesh Reddy:** So, what we've we're planning to implement is Mo, can you share your screen again? Sorry. So, what we're planning to implement is a method to see which of the side scatters are greater. that is side scatter one or two is greater and the program will pick that larger side scatter and compare it with forward scatter and then calculate the size based on that.  
**Surya Pratap Singh:** Mhm. Uhhuh. Uh-huh. Yeah. Yeah.  
**Parvesh Reddy:** So you can see here it'll give you the estimated diameter and what we're planning to do is uh add a function here where we can select which of the original columns we want to use and plot it against  
   
 

### 00:24:39

   
**Surya Pratap Singh:** Yeah. Yeah. Yeah.  
**Parvesh Reddy:** the size directly rather than against scattering. that will make it easier to see the screen, right? Like because I remember in the uh machine that we had that you guys had, you wouldn't see the sizes, right?  
**Surya Pratap Singh:** Yeah. Yeah. Yeah.  
**Parvesh Reddy:** You'd have to assume the size.  
**Surya Pratap Singh:** Yeah. Yeah. Yeah. Actually uh in that machine uh you won't be able to see any size.  
**Parvesh Reddy:** Correct? So, but here we'll be able to directly plot the size versus the columns.  
**Surya Pratap Singh:** Yeah. That is the that is the uh plan actually why we are uh working on the software development. We want to propose a size uh integrated into the soft single software. Everything is in one software only.  
**Parvesh Reddy:** So, what it can do now is it'll plot the size versus one of the other columns. Once it plots that, we can directly pin one of these graphs, whichever graphs you want to see, to the to the front page, the dashboard.  
   
 

### 00:25:45

   
**Surya Pratap Singh:** Yeah. So here we are seeing most of the particles are in 180 nometers actually right?  
**Parvesh Reddy:** Yeah, but these actually are like they have hit the uh edge.  
**Surya Pratap Singh:** Yeah. Okay. Okay. Okay. Yeah.  
**Parvesh Reddy:** So it's like yeah it's hit the lower bound upper bound correct what we need mostly is actually the scatter angles and uh the calculation which  
**Surya Pratap Singh:** lower, lower and upper. Okay. Uh okay. Understood. So probably there is a still modeling parameterization is still pending.  
**Parvesh Reddy:** is larger. So once we get a little bit of those data I think we'll be okay.  
**Surya Pratap Singh:** Okay. Yeah. actually uh they are slightly slow at uh this end actually some Yeah.  
**Parvesh Reddy:** What we can probably do is based on the NTA data we can normalize these curves because from there we'll know what  
**Surya Pratap Singh:** Mhm. Yeah. Uh so today I asked him like uh can they generate uh uh proper data for like a proper nomenclature so that it becomes uh easy for you people to manage.  
   
 

### 00:26:57

   
**Parvesh Reddy:** Sure, no problem.  
**Surya Pratap Singh:** Uh they they will I I will I will submit some data in your drive.  
**Parvesh Reddy:** So this is the UI updates. So Sumit, you can ask whatever questions you had.  
**Surya Pratap Singh:** Yeah. Yes, please.  
**Sumit Malhotra:** Okay. So, uh like my main questions basically based upon uh let's say uh when we are plotting the graphs for different different things. So, the one of the main question is that that already pervased us like what type of graphs and these things we need to consider here and I believe that I will be able to understand here.  
**Surya Pratap Singh:** Yeah.  
**Sumit Malhotra:** Second uh what I did is I'll show you basically in the backend structure I think whatever we are discussing right now I did some of the work in that space also uh basically the size calculation and everything related to the data that we have. So I'll show you quickly uh basically uh first I convert that files into the pocket files and I generated these real graphs. I just want to show you that if these type of graphs is uh okay for you guys to understand or if there are any changes needed in the this space as well.  
   
 

### 00:28:10

   
**Sumit Malhotra:** So I can accordingly manage. So basically I pick a sample of FCS file which is uh this sample one UGISO SEC and in this I am calculating violet forward scatter area versus violet side scatter C1 area.  
**Surya Pratap Singh:** Yeah, that's absolutely fine.  
**Sumit Malhotra:** So right.  
**Surya Pratap Singh:** Like this is a like you copied it from some online sources.  
**Sumit Malhotra:** So no no it is the actual actual FSE data file graph the the sample files that we have here right the the one that the one you gave us right so in this I try to create a graph  
**Surya Pratap Singh:** No. Who supplied it? We supplied. Okay. Okay. Okay. Okay. One microgram I Okay. Okay.  
**Sumit Malhotra:** this it is basically I believe the isotope control graph which shows us the uh certain parameters like where are the exoomes and these things are there so It shows the density at the bottom level the low size exosomes are there. The yellow dot represents basically uh it is a low uh dense area and on the top when we are going up and up.  
   
 

### 00:29:09

   
**Sumit Malhotra:** So the sizes of the exosomes will be increasing here. So this is one of the type of graphs that I try to create. Similarly uh as far as the size calculation I'll show you that as well quickly in the nanofax process with size even with sizes. Yes. So if we going into this at the end here I use the my function one the the in the literature for there is a one my function to calculate the particle sizes right.  
**Surya Pratap Singh:** Yes. Yes. Yes.  
**Sumit Malhotra:** So I used that uh calculation parameters and I tried to calculate the size of each event in each uh molecule here. So it is showing and added these uh lines as well for the size calculation as well.  
**Surya Pratap Singh:** Yeah. Yeah.  
**Sumit Malhotra:** it is showing mostly the data here as well for the size calculation as well with with basis upon the my function right apart from that it uh showed some of the uh you can say in the process data  
**Surya Pratap Singh:** Yeah.  
   
 

### 00:29:56

   
**Surya Pratap Singh:** Yeah. Yeah. Yeah. Understood. Understood. Yeah. Mhm.  
**Sumit Malhotra:** I did today something I'll show you that yes so it is also showing you the distance as well the SCS percentile how much they are normalization in these separate few folders to understand about the data whenever we are training the model also. So it will be helpful for us. So it is calculating the distance from the median as well for each and yeah right so yes so I was I was uh looking into the research upon these particular machines whatever I understand so based upon that I  
**Surya Pratap Singh:** Yeah. Medium values. Okay. Okay. Good. Good. Good. Yeah. Yeah. Yeah. So we can have a distribution curve also, right? Perfect.  
**Sumit Malhotra:** created some of the things. So I just need to get validated that I am going into the right direction is these are the right things that you guys require.  
   
 

### 00:30:49

   
**Sumit Malhotra:** So based upon that I can further go ahead.  
**Surya Pratap Singh:** Yeah, I think uh I think this is this is uh in a right direction. The only thing is like uh uh I'm not sure like these numbers looks very uh close by actually uh I think we can make round off uh instead of putting the floating numbers we can put the roundoff and  
**Sumit Malhotra:** Mhm. Mhm. Mhm.  
**Surya Pratap Singh:** uh because uh uh these are all in nanometer sizes and uh it's always good to have the roundoff numbers instead of floating numbers.  
**Sumit Malhotra:** Mhm. Okay. Okay, I'll do that.  
**Surya Pratap Singh:** And uh yeah that's that should not be a big uh short shot short shot short shot short short shot short shot short shot short shot short shot short shot short shot for you and uh one more thing I  
**Sumit Malhotra:** Mhm.  
**Surya Pratap Singh:** I we think uh perves uh are are we able to uh obtain all the coefficients?  
**Parvesh Reddy:** A, B, and C. Is it uh we're calculating that in the back end, but it's not we're not actually looking at it.  
   
 

### 00:31:45

   
**Surya Pratap Singh:** Yes. Yes. Yes. Okay. Okay. Yeah. But we are able to uh fetch it right.  
**Parvesh Reddy:** It's coming from a lookup table. That's the problem. Um I don't know like we'll have to give a specific size then it'll it can like show you a lookup table.  
**Surya Pratap Singh:** Actually uh uh there was a scientist Sumukha who uh I uh whom I asked for uh some calibration data. Unfortunately he has not furnished those data until now. So I'll make sure like uh once he gives maybe I'll have more proper refractive indexes and then we can we can uh get more better data  
**Parvesh Reddy:** Sure. But uh I'll need another help from you where you if you can give us uh for the nanofax um FCS files.  
**Surya Pratap Singh:** in input files. Now uh I have asked Okay.  
**Parvesh Reddy:** No, no, not the files, but rather which graphs that when you do the experiment, which graphs do you people usually look at?  
   
 

### 00:32:49

   
**Parvesh Reddy:** That'll be helpful for us to generate those specific graphs for example like Yeah.  
**Surya Pratap Singh:** Okay. Okay. Basically one will be scatter plot. Yeah. One will be scatter plot and usually there will be only two things his scatter plot and histograms.  
**Parvesh Reddy:** Yeah. Which scatter plots you usually look at. So those specifically we'll generate and see if we can find some insights from that.  
**Surya Pratap Singh:** uh B printed data that's it yeah uh yeah I'll I'll make sure to let you know what what are the exact now actually uh on x-axis side so x-axis will be uh ssc and uh on no  
**Parvesh Reddy:** Correct. So if you can tell us what those x and y axis are for those we will  
**Surya Pratap Singh:** x will be fsc and y will be ssc and uh one will be side scatter a area versus height Yeah.  
**Parvesh Reddy:** But if you can give us a few examples that would be helpful.  
**Surya Pratap Singh:** Yeah. Yeah. Like uh this is I'm telling by my memory.  
   
 

### 00:33:50

   
**Surya Pratap Singh:** I'll I'll give you the exact uh values with some uh literature as well.  
**Parvesh Reddy:** Yeah, that will be very helpful.  
**Surya Pratap Singh:** Yeah. I'll provide I'll provide and Sumit had any other queries.  
**Sumit Malhotra:** Uh not at the moment like most of them I was clarified by Praves and I just want to make sure that I am working in the right direction here in the back end procedure.  
**Surya Pratap Singh:** Yeah. Yeah like like that's for sure and like uh uh if I I'll come through anything additional values I will add up to per personal I mean on on my own chat as well yeah  
**Parvesh Reddy:** Okay. Yeah, that that works. So um anyone had any other questions? The the costs I will email to you along with uh both. Yeah, I'll email to you and Jen sir.  
**Surya Pratap Singh:** that's it yeah That's  
**Parvesh Reddy:** So yeah that's that's about it from our side. Chari did you have anything to add? We've gone through the UI and Sumit has asked questions.  
   
 

### 00:34:47

   
**Charmi Dholakia:** So the AWS links that we were going we had discussed that we can Okay.  
**Parvesh Reddy:** Did you? Yeah, that um I will send it to them by email directly. I'll CC you also in it.  
**Charmi Dholakia:** Okay. Fine. any if they have if you have any other doubt on it.  
**Parvesh Reddy:** Oh, Surya sir, you had right you wanted to ask something about the architecture.  
**Surya Pratap Singh:** Yeah like uh I mean uh okay sorry uh so chi you prep uh you showed other days the text now uh if it is okay can you share that yeah uh you can share in the file I'll I'll  
**Charmi Dholakia:** Oh yeah, sure.  
**Surya Pratap Singh:** go through and I'll come back uh like uh what what what is like uh where we can help like what we can supply with some methodological things I'll come back Okay,  
**Charmi Dholakia:** Uh-huh. Sure. Sure. Yeah. Uh yeah. I I don't I mean Burves will share it with Surya, right? That architecture  
**Parvesh Reddy:** Yeah, I think the draft is actually already there on the drive.  
   
 

### 00:35:46

   
**Surya Pratap Singh:** but I didn't see uh I did not see like I tried to okay where I can like exercise Architecture  
**Parvesh Reddy:** One second. Let me share my screen. I think it is  
**Surya Pratap Singh:** draft is this one. I think this one I did not open.  
**Parvesh Reddy:** Yeah, if you see architecture draft space one, this file here, the CRM architecture draft one and if you prefer visually  
**Surya Pratap Singh:** Ah, okay. This one I did not open. Sorry. I opened the other files and I felt like, okay, these are old files. Old files. Sorry. Sorry. Okay. Yeah. Yeah.  
**Parvesh Reddy:** I've put the tool architecture here outside yeah  
**Charmi Dholakia:** Thank you. Thank you.  
**Sumit Malhotra:** Okay, thank you. Bye-bye.  
**Abhishek Reddy:** Thank you.  
**Parvesh Reddy:** Vishal did you have something.  
**Vishal Reddy:** Uh Parish we will uh probably what can you just give me a just a quick summary of what happened? I missed two  
**Parvesh Reddy:** Sure. Mo, can you share your screen? We'll quickly show Vishal what we have.  
**Mohith M:** Sure.  
**Abhishek Reddy:** You want to stop recording? Uh for interesting  
**Parvesh Reddy:** Oh yeah. Yeah. Stop  
   
 

### Transcription ended after 00:37:18

*This editable transcript was computer generated and might contain errors. People can also change the text after it was created.*

