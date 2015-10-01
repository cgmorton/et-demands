%Make area weighted annual crop ET for each HUC 10
%Dan McEvoy, September, 2015

cd Z:\USBR_Ag_Demands_Project\CAT_Basins\WashitaOK\gis

%read shapfile
s = shaperead('ETCells.shp');
fnames = fieldnames(s);
fnames = fnames(29:end);

%loop through each HUC
et_weighted = nan(37,length(s)+1);
et_weighted(:,1) = 1979:2015;

for i = 1:length(s)
    fprintf('%d\n',i)
    huc{i} = s(i).HUC10;
    cd Z:\USBR_Ag_Demands_Project\CAT_Basins\WashitaOK\et_demands_py\annual_stats
    files = dir([huc{i} '*']);
    
    ann_et_vol = nan(37,length(files));
    all_crop_area = nan(length(files),1);
    
    %loop through et files
    for j = 1:length(files)
        
        cropid = files(j).name(24:25);
        eval(['crop_area = s(i).CROP_' cropid ';']);

        %convert area from acres to square meters
        crop_area = crop_area*4046.86;

        %load in et data for specific crop
        [num,txt] = xlsread(files(j).name);
        et = num(:,3)/1000;

        %et expressed as volume
        et_vol = et * crop_area;
        
        ann_et_vol(:,j) = et_vol;
        all_crop_area(j) = crop_area;
    end
    
    ann_et_vol_total = sum(ann_et_vol,2);
    all_crop_area_total = sum(all_crop_area);
    
    et_weighted(:,i+1) = (ann_et_vol_total./all_crop_area_total)*1000;
    
end

%write data to a .csv
header = {
            
            
            
    