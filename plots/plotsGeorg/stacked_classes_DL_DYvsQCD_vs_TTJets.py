###########
# imports #
###########

# Standard imports
import ROOT
import os
from array import array
from copy import deepcopy
import math

# RootTools
from RootTools.core.standard import *
# TopEFT
from TopEFT.Tools.helpers import getObjDict, getCollection

# User specific 
from TopEFT.Tools.user import plot_directory
plot_directory_=os.path.join(plot_directory, 'DeepLepton')
plot_directory=plot_directory_

# plot samples definitions
from def_DeepLepton_plots import *

#parser
options = get_parser().parse_args()

# adapted from RootTools (added fillstyle)
def fillStyle( color, style, lineColor = ROOT.kBlack, errors = False):
    def func( histo ):
        lc = lineColor if lineColor is not None else color
        histo.SetLineColor( lc )
        histo.SetMarkerSize( 0 )
        histo.SetMarkerStyle( 0 )
        histo.SetMarkerColor( lc )
        histo.SetFillColor( color )
        histo.SetFillStyle( style)
        histo.drawOption = "hist"
        if errors: histo.drawOption+='E'
        return 
    return func


##############################
# load samples and variables #
##############################

#define samples for electorns and muons
samples=plot_samples(options.version, options.year, options.flavour, options.trainingDate, options.isTestData, options.ptSelection, options.sampleSelection, options.sampleSize, options.predictionPath, options.testDataPath)   
    
# variables to read
read_variables=histo_plot_variables(options.trainingDate, options.version)

#########################
# define plot structure #
#########################

plotDate=samples["trainingDate"]

leptonFlavours=[]
ecalTypes=[]

if samples["leptonFlavour"]=="ele":
    sampleEle=samples["sample"]
    leptonFlavours.append({"Name":"Electron", "ShortName":"ele", "pdgId":11, "sample":sampleEle, "selectionString": "abs(lep_pdgId)==11", "date":plotDate})
    ecalTypes.append({"Name":"All", "selectionString": "abs(lep_etaSc)>=0."})
    ecalTypes.append({"Name":"EndCap", "selectionString": "abs(lep_etaSc)>1.479"})
    ecalTypes.append({"Name":"Barrel", "selectionString": "abs(lep_etaSc)<=1.479"})

if samples["leptonFlavour"]=="muo":
    sampleMuo=samples["sample"]
    leptonFlavours.append({"Name":"Muon", "ShortName":"muo", "pdgId":13, "sample":sampleMuo, "selectionString": "abs(lep_pdgId)==13", "date":plotDate})
    ecalTypes.append({"Name":"All", "selectionString": "abs(lep_eta)>=0."})

pt_cuts=[]
pt_cuts.append({"Name":"pt25toInf","lower_limit":25, "selectionString": "lep_pt>=25."})
if options.ptSelection=='pt_10_to_inf':
    pt_cuts.append({"Name":"pt10to25","lower_limit":10, "upper_limit":25, "selectionString": "lep_pt>=10.&&lep_pt<25."})
    pt_cuts.append({"Name":"pt10toInf","lower_limit":10, "selectionString": "lep_pt>=10."})
else:
    pt_cuts.append({"Name":"pt15to25","lower_limit":15, "upper_limit":25, "selectionString": "lep_pt>=15.&&lep_pt<25."})
    pt_cuts.append({"Name":"pt15toInf","lower_limit":15, "selectionString": "lep_pt>=15."})
    

#PF Candidates
pfCand_plot_binning = {
                'neutral'  : {'mult': [21,0,20],'sumPt': [60,0,20]   },
                'charged'  : {'mult': [71,0,70],'sumPt': [240,0,80]  }, 
                'photon'   : {'mult': [41,0,40],'sumPt': [120,0,40]  }, 
                'electron' : {'mult': [21,0,20],'sumPt': [60,0,20]   }, 
                'muon'     : {'mult': [21,0,20],'sumPt': [60,0,20]   },
             }
pfCand_flavors = pfCand_plot_binning.keys()

isTestData=samples["isTestData"]  #1=true, 0=false


####################################
# loop over samples and draw plots #
####################################

for leptonFlavour in leptonFlavours:
        
    preselectionString=lep_preselection(options.flavour) 
    #preselectionString=leptonFlavour["selectionString"] 

    #define class samples
    samplePrompt    = deepcopy(leptonFlavour["sample"])
    sampleNonPrompt = deepcopy(leptonFlavour["sample"])
    sampleFake      = deepcopy(leptonFlavour["sample"])

    samplePrompt.setSelectionString("(lep_isPromptId"+('' if options.version=='v1' else '_Training')+"==1&&"+preselectionString+")")
    sampleNonPrompt.setSelectionString("(lep_isNonPromptId"+('' if options.version=='v1' else '_Training')+"==1&&"+preselectionString+")")
    sampleFake.setSelectionString("(lep_isFakeId"+('' if options.version=='v1' else '_Training')+"==1&&"+preselectionString+")")

    samplePrompt.name    = "Prompt"
    sampleNonPrompt.name = "NonPrompt"
    sampleFake.name      = "Fake"

    samplePrompt.texName    = "Prompt"
    sampleNonPrompt.texName = "NonPrompt"
    sampleFake.texName      = "Fake"

    samplePrompt.style    = fillStyle(color=ROOT.kCyan, style=3004, lineColor=ROOT.kCyan)
    sampleNonPrompt.style = fillStyle(color=ROOT.kBlue, style=3004, lineColor=ROOT.kBlue)
    sampleFake.style      = fillStyle(color=ROOT.kGray, style=3004, lineColor=ROOT.kGray)

    # Define stack
    mc    = [samplePrompt,sampleNonPrompt,sampleFake]  # A full example would be e.g. mc = [ttbar, ttz, ttw, ...]
    stack = Stack(mc) # A full example would be e.g. stack = Stack( mc, [data], [signal1], [signal2] ) -> Samples in "mc" are stacked in the plot

    for pt_cut in pt_cuts:
        for ecalType in ecalTypes:
                
            # Set some defaults -> these need not be specified below for each plot
            weight = staticmethod(lambda event, sample: 1.)  # could be e.g. weight = lambda event, sample: event.weight
            selectionString = "("+pt_cut["selectionString"]+"&&"+ecalType["selectionString"]+")" # could be a complicated cut
            Plot.setDefaults(stack = stack, weight = weight, selectionString = selectionString, addOverFlowBin='upper')
            plotname='_{sampleSelection}'.format(sampleSelection=options.sampleSelection.split('_')[0])
            # Sequence
            sequence = []

            def make_sumPt( event, sample ):
                for flavor in pfCand_flavors:
                    cands = getCollection( event, 'pfCand_%s'%flavor, ['pt_ptRelSorted'], 'npfCand_%s'%flavor )
                    #print cands
                    setattr( event, 'mult_%s'%flavor, len( cands ) )
                    setattr( event, 'sumPt_%s'%flavor, sum( [ c['pt_ptRelSorted'] for c in cands ], 0. ) )
            sequence.append( make_sumPt )

            #def print_mcmatchId( event, sample ):
            #    if isNonPrompt(event) and event.lep_mvaIdSpring16<0.3 and sample==sample:
            #        print event.lep_mcMatchId

            #def print_class( event, sample ):
            #    assert isPrompt(event) + isNonPrompt(event) + isFake(event)==1, "Should never happen!"

            #    print event.lep_isPromptId, event.lep_isNonPromptId, event.lep_isFakeId, event.lep_mcMatchId, event.lep_mcMatchAny, isPrompt(event), isNonPrompt(event), isFake(event), event.lep_pdgId
            #    #print "Fill", event.lep_isPromptId if ((isPrompt(event) and sample==samplePrompt) or (isNonPrompt(event) and sample==sampleNonPrompt) or (isFake(event) and sample==sampleFake)) else float('nan')
            #    #print "Fill2", (isPrompt(event) and sample==samplePrompt),(isNonPrompt(event) and sample==sampleNonPrompt),(isFake(event) and sample==sampleFake)
            ##sequence.append(print_class)

            # Start with an empty list
            plots = []
            # Add plots

            #Lepton Classes
            plots.append(Plot(name='ClassPrompt'+plotname,
                texX = 'isPrompt', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_isPromptId if options.version=='v1' else lepton.lep_isPromptId_Training,
                binning=[2,0,1],
            ))
            plots.append(Plot(name='ClassNonPrompt'+plotname,
                texX = 'isNonPrompt', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_isNonPromptId if options.version=='v1' else lepton.lep_isNonPromptId_Training,
                binning=[2,0,1],
            ))
            plots.append(Plot(name='ClassFake'+plotname,
                texX = 'isFake', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_isFakeId if options.version=='v1' else lepton.lep_isFakeId_Training,
                binning=[2,0,1],
            ))
            
            if not plotDate==0:
                plots.append(Plot(name='DL_prob_isPrompt'+plotname,
                    texX = 'DL_prob_isPrompt', texY = 'Number of Events',
                    attribute = lambda lepton, sample: lepton.prob_lep_isPromptId if options.version=='v1' else lepton.prob_lep_isPromptId_Training,
                    binning=[33,0,1],
                ))
                plots.append(Plot(name='DL_prob_isNonPrompt'+plotname,
                    texX = 'DL_prob_isNonPrompt', texY = 'Number of Events',
                    attribute = lambda lepton, sample: lepton.prob_lep_isNonPromptId if options.version=='v1' else lepton.prob_lep_isNonPromptId_Training,
                    binning=[33,0,1],
                ))
                plots.append(Plot(name='DL_prob_isFake'+plotname,
                    texX = 'DL_prob_isFake', texY = 'Number of Events',
                    attribute = lambda lepton, sample: lepton.prob_lep_isFakeId if options.version=='v1' else lepton.prob_lep_isFakeId_Training,
                    binning=[33,0,1],
                ))

            #Training Variables
            plots.append(Plot(name='pt'+plotname,
                texX = 'pt', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_pt,
                binning=[100,0,500],
            ))
            plots.append(Plot(name='eta'+plotname,
                texX = 'eta', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_eta,
                binning=[60,-3.2,3.2],
            ))
            #plots.append(Plot(name='phi'+plotname,
            #    texX = 'phi', texY = 'Number of Events',
            #    attribute = lambda lepton, sample: lepton.lep_phi,
            #    binning=[60,-3.2,3.2],
            #))
            plots.append(Plot(name='rho'+plotname,
                texX = 'rho', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_rho,
                binning=[80,0,40],
            ))
            plots.append(Plot(name='innerTrackChi2'+plotname,
                texX = 'innerTrackChi2', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_innerTrackChi2,
                binning=[50,0,5] if leptonFlavour["Name"]=="Muon" else [50,0,10],
            ))
            plots.append(Plot(name='relIso03'+plotname,
                texX = 'relIso03', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_relIso03,
                binning=[90,0,0.5],
            ))
            plots.append(Plot(name='miniRelIsoCharged'+plotname,
                texX = 'miniRelIsoCharged', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_miniRelIsoCharged,
                binning=[90,0,0.5],
            ))
            plots.append(Plot(name='miniRelIsoNeutral'+plotname,
                texX = 'miniRelIsoNeutral', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_miniRelIsoNeutral,
                binning=[90,0,0.5],
            ))
            #plots.append(Plot(name='relIso04'+plotname,
            #    texX = 'relIso04', texY = 'Number of Events',
            #    attribute = lambda lepton, sample: lepton.lep_relIso04,
            #    binning=[90,0,0.7],
            #))
            #plots.append(Plot(name='miniRelIso'+plotname,
            #    texX = 'miniRelIso', texY = 'Number of Events',
            #    attribute = lambda lepton, sample: lepton.lep_miniRelIso,
            #    binning=[90,0,0.5],
            #))
            plots.append(Plot(name='lostOuterHits'+plotname,
                texX = 'lostOuterHits', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_lostOuterHits,
                binning=[16,0,15],
            ))
            plots.append(Plot(name='lostInnerHits'+plotname,
                texX = 'lostInnerHits', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_lostHits,
                binning=[16,0,15],
            ))
            plots.append(Plot(name='trackerLayers'+plotname,
                texX = 'trackerLayers', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_trackerLayers,
                binning=[16,0,15],
            ))
            plots.append(Plot(name='pixelLayers'+plotname,
                texX = 'pixelLayers', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_pixelLayers,
                binning=[16,0,15],
            ))
            plots.append(Plot(name='trackerHits'+plotname,
                texX = 'trackerHits', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_trackerHits,
                binning=[16,0,15],
            ))
            plots.append(Plot(name='innerTrackValidHitFraction'+plotname,
                texX = 'innerTrackValidHitFraction', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_innerTrackValidHitFraction,
                binning=[50,0.9,1.0],
            ))
            plots.append(Plot(name='jetDR'+plotname,
                texX = 'jetDR', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_jetDR,
                binning=[50,0,0.1],
            ))
            plots.append(Plot(name='dxy'+plotname,
                texX = 'dxy', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_dxy,
                binning=[60,-0.03,0.03] if leptonFlavour["Name"]=="Muon" else [60,-0.15,0.15],
            ))
            plots.append(Plot(name='dz'+plotname,
                texX = 'dz', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_dz,
                binning=[60,-0.1,0.1] if leptonFlavour["Name"]=="Muon" else [60,-0.25,0.25],
            ))
            plots.append(Plot(name='errorDxy'+plotname,
                texX = 'errorDxy', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_edxy,
                binning=[50,0,0.004] if leptonFlavour["Name"]=="Muon" else [100,0,0.008],
            ))
            plots.append(Plot(name='errorDz'+plotname,
                texX = 'errorDz', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_edz,
                binning=[50,0,0.01] if leptonFlavour["Name"]=="Muon" else [100,0,0.02],
            ))
            plots.append(Plot(name='d3DwrtPV'+plotname,
                texX = 'd3DwrtPV', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_ip3d,
                binning=[100,0,0.02] if leptonFlavour["Name"]=="Muon" else [100,0,0.04],
            ))
            plots.append(Plot(name='significanceD3DwrtPV'+plotname,
                texX = 'significanceD3DwrtPV', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_sip3d,
                binning=[100,0,8],
            ))
            #plots.append(Plot(name='effectiveArea03'+plotname,
            #    texX = 'EffectiveArea03', texY = 'Number of Events',
            #    attribute = lambda lepton, sample: lepton.lep_EffectiveArea03,
            #    binning=[100,0,0.1] if leptonFlavour["Name"]=="Muon" else [300,0,0.3],
            #))
            plots.append(Plot(name='jetPtRatiov1'+plotname,
                texX = 'pt(lepton)/pt(nearestJet)', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_jetPtRatiov1,
                binning=[50,0,1],
            ))
            plots.append(Plot(name='jetPtRatiov2'+plotname,
                texX = 'pt(lepton)/[rawpt(jet-PU-lep)*L2L3Res+pt(lepton)]', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_jetPtRatiov2,
                binning=[50,0,1.25],
            ))
            plots.append(Plot(name='jetPtRelv1'+plotname,
                texX = 'lepPtTransverseToJetAxisV1', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_jetPtRelv1,
                binning=[100,0,7],
            ))
            plots.append(Plot(name='jetPtRelv2'+plotname,
                texX = 'lepPtTransverseToJetAxisV1', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_jetPtRelv2,
                binning=[200,0,20],
            ))
            plots.append(Plot(name='ptErrTk'+plotname,
                texX = 'ptErrorTrack', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_ptErrTk,
                binning=[100,0,10] if leptonFlavour["Name"]=="Muon" else [100,0,50],
            ))
 
            #plots.append(Plot(name='nTrueInt'+plotname,
            #    texX = 'nTrueInt', texY = 'Number of Events',
            #    attribute = lambda lepton, sample: lepton.nTrueInt,
            #    binning=[55,0,55],
            #))
            plots.append(Plot(name='MVA_TTH'+plotname,
                texX = 'mvaTTH', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_mvaTTH, 
                binning=[30,-1,1],
            ))
            plots.append(Plot(name='MVA_TTV'+plotname,
                texX = 'mvaTTV', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_mvaTTV, 
                binning=[30,-1,1],
            ))


            #plots.append(Plot(name='jetBTagCSV'+plotname,
            #    texX = 'jetBTagCSV', texY = 'Number of Events',
            #    attribute = lambda lepton, sample: lepton.lep_jetBTagCSV, 
            #    binning=[30,0,1],
            #))
            plots.append(Plot(name='jetBTagDeepCSV'+plotname,
                texX = 'jetBTagDeepCSV', texY = 'Number of Events',
                attribute = lambda lepton, sample: lepton.lep_jetBTagDeepCSV, 
                binning=[30,0,1],
            ))
            #plots.append(Plot(name='jetBTagDeepCSVCvsB'+plotname,
            #    texX = 'jetBTagDeepCSVCvsB', texY = 'Number of Events',
            #    attribute = lambda lepton, sample: lepton.lep_jetBTagDeepCSVCvsB, 
            #    binning=[30,0,1],
            #))
            #plots.append(Plot(name='jetBTagDeepCSVCvsL'+plotname,
            #    texX = 'jetBTagDeepCSVCvsL', texY = 'Number of Events',
            #    attribute = lambda lepton, sample: lepton.lep_jetBTagDeepCSVCvsL, 
            #    binning=[30,0,1],
            #))

            #PF Cands
            for flavor in pfCand_flavors:
                plots.append(Plot(name='pfCands_mult_%s%s'%(flavor,plotname),
                    texX = 'mult_%s'%flavor, texY = 'Number of Events',
                    attribute = "mult_%s"%flavor,
                    binning=pfCand_plot_binning[flavor]['mult'],
                ))
                plots.append(Plot(name='pfCands_sumPt_%s%s'%(flavor,plotname),
                    texX = 'sumPt_%s'%flavor, texY = 'Number of Events',
                    attribute = "sumPt_%s"%flavor,
                    binning=pfCand_plot_binning[flavor]['sumPt'],
                ))

            #Electron specific
            if leptonFlavour["Name"]=="Electron":

                plots.append(Plot(name='etaSc'+plotname,
                    texX = 'etaSc', texY = 'Number of Events',
                    attribute = lambda lepton, sample: lepton.lep_etaSc,
                    binning=[60,-3,3],
                ))
                plots.append(Plot(name='sigmaIetaIeta'+plotname,
                    texX = 'sigmaIetaIeta', texY = 'Number of Events',
                    attribute = lambda lepton, sample: lepton.lep_sigmaIEtaIEta,
                    binning=[30,0,0.06],
                ))
                plots.append(Plot(name='full5x5SigmaIetaIeta'+plotname,
                    texX = 'full5x5_sigmaIetaIeta', texY = 'Number of Events',
                    attribute = lambda lepton, sample: lepton.lep_full5x5_sigmaIetaIeta,
                    binning=[30,0,0.06],
                ))
                plots.append(Plot(name='dEtaInSeed'+plotname,
                    texX = 'dEtaInSeed', texY = 'Number of Events',
                    attribute = lambda lepton, sample: lepton.lep_dEtaInSeed,
                    binning=[20,-0.04,0.04],
                ))
                plots.append(Plot(name='dPhiScTrkIn'+plotname,
                    texX = 'dPhiScTrkIn', texY = 'Number of Events',
                    attribute = lambda lepton, sample: lepton.lep_dPhiScTrkIn,
                    binning=[30,-0.3,0.3],
                ))
                plots.append(Plot(name='dEtaScTrkIn'+plotname,
                    texX = 'dEtaScTrkIn', texY = 'Number of Events',
                    attribute = lambda lepton, sample: lepton.lep_dEtaScTrkIn,
                    binning=[50,-1,1],
                ))
                plots.append(Plot(name='eInvMinusPInv'+plotname,
                    texX = '|1/E-1/p|', texY = 'Number of Events',
                    attribute = lambda lepton, sample: lepton.absEInvMinusPInv,
                    binning=[30,0,0.20],
                ))
                plots.append(Plot(name='convVeto'+plotname,
                    texX = 'convVeto', texY = 'Number of Events',
                    attribute = lambda lepton, sample: lepton.lep_convVeto,
                    binning=[2,0,1],
                ))
                plots.append(Plot(name='hadronicOverEm'+plotname,
                    texX = 'hadronicOverEm', texY = 'Number of Events',
                    attribute = lambda lepton, sample: lepton.lep_hadronicOverEm,
                    binning=[30,0,0.15],
                ))
                plots.append(Plot(name='r9'+plotname,
                    texX = 'r9', texY = 'Number of Events',
                    attribute = lambda lepton, sample: lepton.lep_r9,
                    binning=[100,0,1],
                ))
            #Muon specific
            if leptonFlavour["Name"]=="Muon":
                
                plots.append(Plot(name='segmentCompatibility'+plotname,
                    texX = 'segmentCompatibility', texY = 'Number of Events',
                    attribute = lambda lepton, sample: lepton.lep_segmentCompatibility,
                    binning=[10,0,1],
                ))
                plots.append(Plot(name='muonInnerTrkRelErr'+plotname,
                    texX = 'muonInnerTrkRelErr', texY = 'Number of Events',
                    attribute = lambda lepton, sample: lepton.lep_muonInnerTrkRelErr,
                    binning=[50,0,0.05],
                ))
                plots.append(Plot(name='isGlobalMuon'+plotname,
                    texX = 'isGlobalMuon', texY = 'Number of Events',
                    attribute = lambda lepton, sample: lepton.lep_isGlobalMuon,
                    binning=[2,0,1],
                ))
                plots.append(Plot(name='chi2LocalPosition'+plotname,
                    texX = 'chi2LocalPosition', texY = 'Number of Events',
                    attribute = lambda lepton, sample: lepton.lep_chi2LocalPosition,
                    binning=[100,0,10],
                ))
                plots.append(Plot(name='chi2LocalMomentum'+plotname,
                    texX = 'chi2LocalMomentum', texY = 'Number of Events',
                    attribute = lambda lepton, sample: lepton.lep_chi2LocalMomentum,
                    binning=[100,0,30],
                ))
                plots.append(Plot(name='gobalTrackChi2'+plotname,
                    texX = 'gobalTrackChi2', texY = 'Number of Events',
                    attribute = lambda lepton, sample: lepton.lep_globalTrackChi2,
                    binning=[50,0,3],
                ))
                plots.append(Plot(name='gobalTrackProb'+plotname,
                    texX = 'gobalTrackProb', texY = 'Number of Events',
                    attribute = lambda lepton, sample: lepton.lep_glbTrackProbability,
                    binning=[50,0,8],
                ))
                plots.append(Plot(name='caloCompatibility'+plotname,
                    texX = 'caloCompatibility', texY = 'Number of Events',
                    attribute = lambda lepton, sample: lepton.lep_caloCompatibility,
                    binning=[50,0,1],
                ))
                plots.append(Plot(name='trkKink'+plotname,
                    texX = 'trkKink', texY = 'Number of Events',
                    attribute = lambda lepton, sample: lepton.lep_trkKink,
                    binning=[100,0,200],
                ))
            #other Variables
            #plots.append(Plot(name='mcMatchId'+plotname,
            #    texX = 'mcMatchId', texY = 'Number of Events',
            #    attribute = lambda lepton, sample: lepton.lep_mcMatchId,
            #    binning=[61,-30,30],
            #))
            #plots.append(Plot(name='mcMatchAny'+plotname,
            #    texX = 'mcMatchAny', texY = 'Number of Events',
            #    attribute = lambda lepton, sample: lepton.lep_mcMatchAny,
            #    binning=[61,-30,30],
            #))
            #plots.append(Plot(name='pdgId'+plotname,
            #    texX = 'pdgId', texY = 'Number of Events',
            #    attribute = lambda lepton, sample: lepton.lep_pdgId,
            #    binning=[61,-30,30],
            #))
            

            #plots.append(Plot( name = "fancy_variable",
            #    texX = 'Number of tracker hits squared', texY = 'Number of Events',
            #    attribute = lambda event, sample: event.fancy_variable, # <--- can use any 'event' attribute, including the ones we define in 'sequence'    binning=[30,0,900],
            #))


            # Fill everything.
            plotting.fill(plots, read_variables = read_variables, sequence = sequence)

            #
            # Helper: Add text on the plots
            #
            def drawObjects( plotData, dataMCScale, lumi_scale ):
                tex = ROOT.TLatex()
                tex.SetNDC()
                tex.SetTextSize(0.04)
                tex.SetTextAlign(11) # align right
                lines = [
                  (0.25, 0.95, 'TestData' if isTestData else 'TrainData'),
                  (0.55, 0.95, pt_cut["Name"]+" "+ecalType["Name"]+" "+leptonFlavour["Name"]+"s")
                ]
                return [tex.DrawLatex(*l) for l in lines]

            # Draw a plot and make it look nice-ish
            def drawPlots(plots, dataMCScale):
              for log in [False, True]:
                if options.isTestData==99:
                    plot_directory_=(os.path.join(
                                            plot_directory,
                                            'predictions',
                                            str(options.year),
                                            options.flavour,
                                            options.sampleSelection,
                                            str(options.trainingDate),
                                            'histograms', pt_cut["Name"]+"_"+ecalType["Name"], ("log" if log else "lin")
                                            ))
                else:
                    plot_directory_ = (os.path.join(
                                                    plot_directory,
                                                    'training_input_histogramms',
                                                    pt_cut["Name"]+"_"+ecalType["Name"], ("log" if log else "lin")
                                                    ))
                for plot in plots:
                  #if not max(l[0].GetMaximum() for l in plot.histos): continue # Empty plot
                  
                  plotting.draw(plot,
                    plot_directory = plot_directory_,
                    #ratio = {'yRange':(0.1,1.9)} if not args.noData else None,
                    logX = False, logY = log, sorting = True,
                    yRange = (0.03, "auto") if log else (0.001, "auto"),
                    scaling = {},
                    legend = [ (0.15,0.9-0.03*sum(map(len, plot.histos)),0.9,0.9), 2],
                    drawObjects = drawObjects( False, dataMCScale , lumi_scale = -1 ),
                    copyIndexPHP = True
                  )


            # Draw the plots
            drawPlots(plots, dataMCScale = -1)

