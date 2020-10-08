%% Matpower export to csv %%

%% Input
mpc = case9_blv; % Matpower case
n_bus = 9; % Number of buses of the system

%% Conversion of the matrices to csv
filename = sprintf('bus_%dbus.csv',n_bus);
writematrix(mpc.bus,filename);
filename = sprintf('gen_%dbus.csv',n_bus);
writematrix(mpc.gen,filename);
filename = sprintf('branch_%dbus.csv',n_bus);
writematrix(mpc.branch,filename);
filename = sprintf('gencost_%dbus.csv',n_bus);
writematrix(mpc.gencost,filename);
filename = sprintf('baseMVA_%dbus.csv',n_bus);
writematrix(mpc.baseMVA,filename);