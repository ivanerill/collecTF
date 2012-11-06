# Forms for curation wizard
from django import forms
from models import *
import bioutils
from makeobj import *
import sitesearch


class PublicationForm(forms.Form):
    """Publication selection form"""
    pub = forms.ChoiceField(widget=forms.RadioSelect(),
                            label="Publications")

class GenomeForm(forms.Form):
    """Form for submission of genome and TF accession numbers and others"""
    TF = forms.ModelChoiceField(queryset=TF.objects.all(),
                                label="TF")
    TF_type = forms.ChoiceField(Curation.TF_TYPE, label="TF structure")
    TF_function = forms.ChoiceField(Curation.TF_FUNCTION, label="TF function")
    genome_accession = forms.CharField(label="Genome NCBI accession number")
    # form fields
    # TF_species_same / TF_species and
    # site_species_same / site_species
    # are redundant.  When the form is displayed, the curator can either input
    # TF and site species manually, or he can select the option that they are
    # same species with genome. If they are same species with genome, he doesn't
    # need to input whole species name
    TF_species_same = forms.BooleanField(label="TF-species is same with genome",
                                         required=False)
    TF_accession = forms.CharField(label="TF accession number") 

    site_species_same = forms.BooleanField(label="site-species is same with genome",
                                           required=False)

    TF_species = forms.CharField(label="Organism of origin for reported TF", required=False)
    site_species = forms.CharField(label="Organism TF binding sites are reported in",
                                   required=False)
    
    def clean_genome_accession(self):
        genome_accession = self.cleaned_data['genome_accession']
        # remove version
        genome_accession = genome_accession.split('.')[0]
        print genome_accession
        try: # to retrieve genome from database (if exists)
            g = Genome.objects.get(genome_accession=genome_accession)
        except Genome.DoesNotExist: # try to retrieve from NCBI database
            genome_rec = bioutils.get_genome(genome_accession)
            if not genome_rec:
                msg = "Cannot fetch genome record from NCBI. Check accession number."
                raise forms.ValidationError(msg)
            # create Genome object
            make_genome(genome_rec)
            # create all Genome objects for each gene on that genome
            make_all_genes(genome_rec)
        return genome_accession

    def clean_TF_accession(self):
        TF_accession = self.cleaned_data['TF_accession']
        # remove version
        TF_accession = TF_accession.split('.')[0]
        try:
            TF_instance = TFInstance.objects.get(protein_accession=TF_accession)
        except TFInstance.DoesNotExist:
            TF_rec = bioutils.get_TF(TF_accession)
            if not TF_rec:
                msg = "Cannot fetch protein record from NCBI. Check accession number."
                raise forms.ValidationError(msg)
            # create TFInstance object
            make_TF_instance(TF_rec)
        return TF_accession

    def clean(self):
        # check if either site-species or site-species-same is filled
        # check if either TF-species or TF-species-same is filled
        cd = self.cleaned_data
        if not (cd['TF_species'] or cd['TF_species_same']):
            self._errors['TF_species'] = self.error_class([u"Invalid TF species"])
        if not (cd['site_species'] or cd['site_species_same']):
            self._errors['site_species'] = self.error_class([u"Invalid site species"])
        return cd

    def clean_TF_species(self):
        # clean TF_species field. If TF_species_same checkbox is selected, assign
        # species data to cleaned data. In that case, it is important that
        # clean_genome is called BEFORE clean_TF_species, because genome is
        # needed to extract species information.
        cd = self.cleaned_data
        if cd['TF_species_same']:
            tf_species = self.clean_species("TF_species")
        else:
            tf_species = cd['TF_species']
        return tf_species

    def clean_site_species(self):
        # same with clean_TF_species function, but for site_species field
        cd = self.cleaned_data
        if cd['site_species_same']:
            site_species = self.clean_species("site_species")
        else:
            site_species = cd['site_species']
        return site_species

    def clean_species(self, field):
        # Helper function for clean_TF_species and clean_site_species
        cd = self.cleaned_data
        genome_accession = self.cleaned_data['genome_accession']
        genome = Genome.objects.get(genome_accession=genome_accession)
        if not genome:
            msg = u"Invalid genome accession number"
            self._errors[field] = self.error_class([msg])
        return genome.strain.name


class TechniquesForm(forms.Form):
    """Form to enter experimental techniques used to identify TFBS"""
    contains_promoter_data = forms.BooleanField(required=False,
                                                label="The manuscript contains promoter information")
    contains_expression_data = forms.BooleanField(required=False,
                                                  label="The manuscript contains expression data")
    # get available techniques from db
    techniques = forms.ModelMultipleChoiceField(
        queryset=ExperimentalTechnique.objects.order_by('name'),
        widget=forms.CheckboxSelectMultiple(),
        label="Techniques")
    experimental_process = forms.CharField(widget=forms.Textarea, required=False,
                                           label="Experimental process")
                                           
    forms_complex = forms.BooleanField(required=False, label="TF complex")
    complex_notes = forms.CharField(widget=forms.Textarea, required=False,
                                    label="Notes")

class SiteReportForm(forms.Form):
    """Form to input the list of sites reported in the paper"""
    sites = forms.CharField(widget=forms.Textarea,
                            label="")

    def clean_sites(self):
        sites_cd = self.cleaned_data['sites']
        sites = sitesearch.parse_site_input(sites_cd)
        if not sites:
            raise forms.ValidationError("ambiguous DNA sequence")
        return sites_cd
        

class SiteExactMatchForm(forms.Form):
    """Form to select and match reported sites to their equivalents in the
    genome. This form displays only exact matches (i.e. ones that is present in
    genome exactly). If the site is not found in the genome 'exactly', it is
    searched 'softly' and presented in the next form, SiteSoftMatchForm."""
    # all form fields are created dynamically. No static field def here
    pass

class SiteSoftMatchForm(forms.Form):
    """Form displaying results of 'soft' search. Match sites are not exactly
    same with the query sequence, but similar."""
    # No static def either here.
    pass

class SiteRegulationForm(forms.Form):
    """This form is displayed after SiteSoftMatchForm. After the user selects
    site equivalent for each reported site, in this form, surrounding genes to
    the site are displayed. For each gene, it can be (un)checked whether site
    regualates gene (or not).

    Like the previous two forms, all fields in this form are created
    dynamically, based on which genome positions are selected in the previous
    two forms as site equivalents."""
    pass

class CurationReviewForm(forms.Form):
    """Form to see all data entered so far. The last step to submit curation."""
    choices = ((None, "None"),) + Curation.REVISION_REASONS
    revision_reasons = forms.ChoiceField(choices=choices,
                                         label="Revision required")
    confidence = forms.BooleanField(required=False,
                                    label="I am confident of the results reported in this manuscript.")
    NCBI_submission_ready = forms.BooleanField(required=False,
                                               label="Curation is ready to submit to NCBI.")
                                               
    paper_complete = forms.BooleanField(required=False,
                                        label="Curation for this paper is complete.")
    notes = forms.CharField(widget=forms.Textarea, required=False, label="Notes")
    confirm = forms.BooleanField(required=True,
                                 label="I want to submit this curation")
