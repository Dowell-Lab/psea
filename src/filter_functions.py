import pandas as pd
import os

def validate_input_files(values_file, binary_attribute_file, sample_name):
    """ This function reads in the input csv files as dataframes, 
    and validates if the input files exist and have the required 'sample_name' columns. """
    
    if not os.path.isfile(binary_attribute_file):
        raise FileNotFoundError(f"Binary attribute file '{binary_attribute_file}' not found.")
    if not os.path.isfile(values_file):
        raise FileNotFoundError(f"Values file '{values_file}' not found.")
    
    binary_df = pd.read_csv(binary_attribute_file, index_col=0)
    values_df = pd.read_csv(values_file, index_col=0)
    
    if sample_name not in binary_df.columns:
        raise ValueError(f"Sample column labeled '{sample_name}' not found in the binary attribute file.")
    if sample_name not in values_df.columns:
        raise ValueError(f"Sample column labeled '{sample_name}' not found in the values file.")
    
    return binary_df, values_df

def filter_comorbidities(binary_df, patient_comorbid_threshold, min_comorbids_percent, max_comorbids_percent, sample_name):
    """ This function filters the comorbidity data based on the user defined thresholds. """
    total_samples = binary_df.shape[0]

    if patient_comorbid_threshold < 0:
        raise ValueError("Patient comorbid threshold must be a positive number.")
    if not (0 <= min_comorbids_percent <= 1 and 0 <= max_comorbids_percent <= 1):
        raise ValueError("Comorbid percentage thresholds must be between 0 and 1.")

    # Filter out patients without comorbidities
    filtered_df = binary_df[binary_df.drop(columns=[sample_name]).sum(axis=1) >= patient_comorbid_threshold]
    df_noname = filtered_df.drop(columns=[sample_name])

    # Calculate percent occurrence of comorbidities
    n_comorbid = df_noname.sum(axis=0).to_frame()
    n_comorbid.columns = ["n"]
    n_comorbid["binary_attribute"] = n_comorbid.index
    n_comorbid["percent"] = n_comorbid["n"]/total_samples

    # Filter comorbidities based on prevalence thresholds
    n_comorbid_include = n_comorbid[n_comorbid["percent"]<max_comorbids_percent]
    n_comorbid_include = n_comorbid_include[n_comorbid_include["percent"]>min_comorbids_percent]
    n_comorbid_exclude = n_comorbid[~n_comorbid.index.isin(n_comorbid_include.index)]
    
    # Get the list of comorbidities to keep
    comorbids_to_keep = n_comorbid_include.index.tolist()
    
    # Create filtered dataframe with only the selected comorbidities
    columns_to_keep = [sample_name] + comorbids_to_keep
    filtered_binary_df = filtered_df[columns_to_keep]
    
    return filtered_binary_df, n_comorbid_include, n_comorbid_exclude

def filter_gene_expression(values_df, individual_expression_threshold, min_mean_expression, sample_name):
    """ This function filters the gene expression data based on the user defined thresholds. """
    expression_df_nosamples = values_df.drop(columns=[sample_name])

    # Filter individuals (rows) where all gene expression values are below the threshold
    individual_mask = expression_df_nosamples.apply(lambda row: (row >= individual_expression_threshold).any(), axis=1)
    expression_df_filtered = values_df[individual_mask]
    expression_df_nosamples = expression_df_filtered.drop(columns=[sample_name])

    # Calculate mean expression
    meansdf = expression_df_nosamples.mean(axis=0).to_frame()
    meansdf.columns = ["mean_value"]
    meansdf["valuename"] = meansdf.index

    if min_mean_expression < 0:
        raise ValueError("Minimum mean expression threshold must be non-negative.")

    # Filter genes based on mean expression threshold
    meansdf_include = meansdf[meansdf["mean_value"] > min_mean_expression]
    meansdf_exclude = meansdf[~meansdf.index.isin(meansdf_include.index)]
    
    # Get the list of genes to keep
    genes_to_keep = meansdf_include.index.tolist()
    
    # Create filtered dataframe with only the selected genes
    columns_to_keep = [sample_name] + genes_to_keep
    filtered_values_df = expression_df_filtered[columns_to_keep]

    return filtered_values_df, meansdf_include, meansdf_exclude

def save_filtered_dataframes(filtered_binary_df, 
                            filtered_values_df,
                            n_comorbid_include, 
                            n_comorbid_exclude, 
                            filtered_binary_attribute_file, 
                            filtered_values_file,
                            include_binary_attribute_file, 
                            exclude_binary_attribute_file, 
                            meansdf_include, 
                            meansdf_exclude, 
                            include_values_file, 
                            exclude_values_file):
    """ This function saves the filtered dataframes and include/exclude lists to CSV files. """
    
    # Ensure directories exist
    os.makedirs(os.path.dirname(filtered_binary_attribute_file), exist_ok=True)
    os.makedirs(os.path.dirname(filtered_values_file), exist_ok=True)
    os.makedirs(os.path.dirname(include_binary_attribute_file), exist_ok=True)
    os.makedirs(os.path.dirname(exclude_binary_attribute_file), exist_ok=True)
    os.makedirs(os.path.dirname(include_values_file), exist_ok=True)
    os.makedirs(os.path.dirname(exclude_values_file), exist_ok=True)
    
    # Save the filtered dataframes (main output for AREA)
    filtered_binary_df.to_csv(filtered_binary_attribute_file)
    print(f"Filtered binary attribute dataframe saved to {filtered_binary_attribute_file}")
    
    filtered_values_df.to_csv(filtered_values_file)
    print(f"Filtered values dataframe saved to {filtered_values_file}")
    
    # Save include comorbid list (for reference)
    n_comorbid_include[["binary_attribute"]].to_csv(include_binary_attribute_file, header=False, index=False)
    print(f"Included comorbid list saved to {include_binary_attribute_file}")
    
    # Save excluded comorbid list (for reference)
    n_comorbid_exclude[["binary_attribute"]].to_csv(exclude_binary_attribute_file, header=False, index=False)
    print(f"Excluded comorbid list saved to {exclude_binary_attribute_file}")
    
    # Save included expression list (for reference)
    meansdf_include[["valuename"]].to_csv(include_values_file, header=False, index=False)
    print(f"Included expression list saved to {include_values_file}")
    
    # Save excluded expression list (for reference)
    meansdf_exclude[["valuename"]].to_csv(exclude_values_file, header=False, index=False)
    print(f"Excluded expression list saved to {exclude_values_file}")

def run_filtering(patient_comorbid_threshold, 
                  min_comorbids_percent, 
                  max_comorbids_percent, 
                  individual_expression_threshold, 
                  min_mean_expression, 
                  values_file, 
                  binary_attribute_file, 
                  sample_name, 
                  filtered_values_file,
                  filtered_binary_attribute_file,
                  include_values_file, 
                  include_binary_attribute_file, 
                  exclude_values_file, 
                  exclude_binary_attribute_file):
    
    """ This is the main function that runs comorbidity and gene expression filtering. """
    try:
        # Validate input files and load data
        binary_df, values_df = validate_input_files(values_file, 
                                                    binary_attribute_file, 
                                                    sample_name)

        # Comorbidity filtering
        filtered_binary_df, n_comorbid_include, n_comorbid_exclude = filter_comorbidities(binary_df, 
                                                                                          patient_comorbid_threshold, 
                                                                                          min_comorbids_percent, 
                                                                                          max_comorbids_percent, 
                                                                                          sample_name)
        
        print("Passing comorbidities based on filtering thresholds:")
        print(n_comorbid_include)
        print("Excluded comorbidities based on filtering thresholds:")
        print(n_comorbid_exclude)

        # Gene expression filtering
        filtered_values_df, meansdf_include, meansdf_exclude = filter_gene_expression(values_df, 
                                                                                      individual_expression_threshold, 
                                                                                      min_mean_expression, 
                                                                                      sample_name)
        
        print("Passing genes based on mean threshold for expression:")
        print(meansdf_include)
        print("Excluded genes based on mean threshold for expression:")
        print(meansdf_exclude)
        
        # Save filtered dataframes and lists
        save_filtered_dataframes(filtered_binary_df, 
                                 filtered_values_df,
                                 n_comorbid_include, 
                                 n_comorbid_exclude, 
                                 filtered_binary_attribute_file,
                                 filtered_values_file,
                                 include_binary_attribute_file, 
                                 exclude_binary_attribute_file, 
                                 meansdf_include, 
                                 meansdf_exclude, 
                                 include_values_file, 
                                 exclude_values_file)
    
    except Exception as e:
        print(f"Error occurred during filtering: {e}")