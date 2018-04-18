import _util as util
import os

def main(ini_path):
    """Check new daily static output to historical outputs

    Args:
        ini_path (str): file path of the project INI file
    Returns:
        None
    """
    logging.info('\nChecking daily_stats output against historical ouput files. Only crop 03 for now.')
    
    config = util.read_ini(ini_path, section='CROP_ET')
    try:
        project_ws = config.get('CROP_ET', 'project_folder')
    except:
        logging.error(
            'project_folder parameter must be set in the INI file, exiting')
        return False
    
    project_ws = 'D:\et-demands\example'
    
    daily_stats_path =os.path.join(project_ws, 'daily_stats')
    validation_stats_path =os.path.join(project_ws, 'validation_files')
    
    ex_crop_list = ['03', '07', '11', '13','38','58','60','67','78','79']
    
    for crop in ex_crop_list:
        print(crop)
        
# FILE COMPARISON METHOD WORKS, BUT RUNNING INTO ROUNDING ISSUES WITH CODE DIFFERENCES         
#        with open(os.path.join(daily_stats_path,'12090105_crop_{}.csv').format(crop)) as f1, open(os.path.join(validation_stats_path,
#        'daily_stats','12090105_daily_crop_{}.csv').format(crop)) as f2:
#            w1 = set(f1)
#            w2 = set(f2)
#            
#        with open(os.path.join(validation_stats_path,'Differences_crop_{}.txt').format(crop),'w+') as fout:
#            fout.writelines(sorted(w1 - w2))
#            
#        print('Crop {} Differences from Original Output:').format(crop)    
#            
#        with open(os.path.join(validation_stats_path,'Differences_crop_{}.txt').format(crop)) as f:
#            print f.read()    



        
    
