-- test script
-- th test.lua -model ConvVAE -modelPath training_result/ConvVAE/net_epoch_17.t7 -testdataPath /home/mlpa/Workspace/dataset/VAE_anomally_detection/test 2>&1 | tee log_test_ConvVAE.log

-- Load dependencies
local optim = require 'optim';
local gnuplot = require 'gnuplot';
local image = require 'image';
local display = require 'display';
local hdf5 = require 'hdf5'
local cuda = pcall(require, 'cutorch'); -- Use CUDA if available
local hasCudnn, cudnn = pcall(require, 'cudnn'); -- Use cuDNN if available
util = paths.dofile('util/util.lua')
-- require 'dpnn';

debug_display = false;
local function print_debug(...)
	if debug_display then print(...) end
end

--=============================================================================
-- Command-line options
--=============================================================================
local cmd = torch.CmdLine();
-- major parameters
cmd:option('-model', 'ConvVAE', 'Model: AE|SparseAE|DeepAE|ConvAE|UpconvAE|DenoisingAE|Seq2SeqAE|VAE|CatVAE|WTA-AE')
cmd:option('-modelPath', '', 'Path to trained model')
cmd:option('-batchSize', 1, 'Batch for testing (default: 1)')
-- data loading
cmd:option('-testdataPath', '', 'Path for test data folder')
-- cpu / gpu
cmd:option('-cpu', false, 'CPU only (useful if GPU memory is too low)')
cmd:option('-gpu', 1, 'GPU index')
-- output
cmd:option('-outputPath', 'test_result', 'Path for saving test results')
-- display
cmd:option('-display', 0, 'Whether use display or not')
cmd:option('-display_freq', 3, 'Display frequency')

local opt = cmd:parse(arg);

assert(paths.filep(opt.modelPath), "Model path is not a proper one")
-- because the below command cannot handle link
-- assert(paths.dirp(opt.testdataPath), "There is not directory named " .. opt.testdataPath)

if 1 == opt.cpu then
	cuda = false;
else
	cuda = true;	
end
if hasCudnn and cuda then 
	opt.cudnn = 1 
end

if opt.model == 'DenoisingAE' then
	opt.denoising = false; -- Disable "extra" denoising
end

print(opt)


--=============================================================================
-- Set up Torch
--=============================================================================
print('Setting up');
torch.setdefaulttensortype('torch.FloatTensor');
torch.manualSeed(854);
if cuda then
	require 'cunn';
	cutorch.manualSeed(torch.random());
end


--=============================================================================
-- Load data and Network
--=============================================================================
-- check file existance
local inputFileList = {}
for file in paths.files(opt.testdataPath, ".h5") do
	table.insert(inputFileList, file);
end
assert(nil ~= next(inputFileList), "There is no proper input file at " .. opt.testdataPath)
table.sort(inputFileList) -- ascending

local XTrainFile = hdf5.open(paths.concat(opt.testdataPath, inputFileList[1]), 'r');
local dataDim = XTrainFile:read('/data'):dataspaceSize()
XTrainFile:close();
local sampleLength, sampleWidth, sampleHeight = dataDim[2], dataDim[3], dataDim[4]
print(('Data dim: %d x %d x %d'):format(sampleLength, sampleHeight, sampleWidth))

local function load_data_from_file(inputFileName)
	local readFile = hdf5.open(paths.concat(opt.testdataPath, inputFileName), 'r');
	local dim = readFile:read('data'):dataspaceSize();
	local numSamples = dim[1];
	print_debug(('Reading data from %s : %d samples'):format(
		inputFileName, numSamples))
	local data = readFile:read('data'):all();
	readFile:close();

	return data
end

-- load model
if string.find(opt.model, 'VAE') then
	require 'modules/Gaussian'
end
Model = util.load_model(opt.modelPath, opt)
local autoencoder = Model.autoencoder;

--=============================================================================
-- Data buffer and GPU
--=============================================================================
local x    = torch.Tensor(opt.batchSize, sampleLength, sampleHeight, sampleWidth)
local xHat = torch.Tensor(opt.batchSize, sampleLength, sampleHeight, sampleWidth)

if cuda then
	print('Transferring to gpu...')
	require 'cunn'
	cutorch.setDevice(opt.gpu)
	
	-- data buffer
	x    = x:cuda()
	xHat = xHat:cuda()

	-- network
	autoencoder:cuda();
	print(autoencoder)
	
	print('done')
else
	print('Running model on CPU')
end

--=============================================================================
-- Test
--=============================================================================
-- for result saving
local output_dir = paths.concat(opt.outputPath, opt.model)
paths.mkdir(opt.outputPath)
paths.mkdir(output_dir)

print('Testing...')
autoencoder:evaluate()

local function get_scenario_string(input_string)
	-- parsing scenario part: [SCENARIO_NAME]_video_[NUMBER]
	count = 0;
	local scenario_string = ''
	for token in string.gmatch(input_string, "[^%s_]+") do
		scenario_string = scenario_string .. token
		count = count + 1;
		if 3 > count then 
			scenario_string = scenario_string .. '_'
		else
			break 
		end
	end
	return scenario_string;
end

for k = 1, #inputFileList do
	print('Test with ' .. inputFileList[k])
	local inputScenario = get_scenario_string(inputFileList[k])

	-- load data
	data = load_data_from_file(inputFileList[k]);
	local numSamples = data:size(1)
	local costs = {};
	for i = 1, numSamples, opt.batchSize do
		x:copy(data:sub(i,i+opt.batchSize-1))
		xHat = autoencoder:forward(x)

		-- reconstruction cost
		local cur_cost = torch.norm(xHat - x);
		table.insert(costs, cur_cost);

		-- draw network result
		if opt.display > 0 and i % opt.display_freq == 0 then					
			local batch_index = math.max(1, math.floor(opt.batchSize * 0.5));
			local frame_index = math.max(1, math.floor(sampleLength * 0.5));
			print_debug(('input_frame (%d x %d x %d x %d) at %d'):format(
				x:size(1), x:size(2), x:size(3), x:size(4), batch_index))
			local input_frame = x[batch_index][frame_index];					
			print_debug(('output_frame (%d x %d x %d x %d) at %d'):format(
				xHat:size(1), xHat:size(2), xHat:size(3), xHat:size(4), batch_index))
			local output_frame = xHat[batch_index][frame_index];
			print_debug('display')

			disp_in_win = display.image(input_frame, {win=disp_in_win, title='test input'})
			disp_out_win = display.image(output_frame, {win=disp_out_win, title='test output'})
		end
	end

	-- save to text file
	local text_file = io.open(paths.concat(output_dir, ('%s_%s.txt'):format(inputScenario, opt.model)), 'w')
	for i = 1, #costs do
		text_file:write(("%.18e\n"):format(costs[i]));
	end
	text_file:close();

	-- -- Plot training curve(s)
	-- local plots = {{'Reconstruction costs', torch.linspace(1, #costs, #costs), torch.Tensor(costs), '-'}}
	-- gnuplot.pngfigure(paths.concat(output_dir, (inputScenario .. '_costs.png')))
	-- gnuplot.plot(table.unpack(plots))
	-- gnuplot.ylabel('Cost')
	-- gnuplot.xlabel('Time (sample index)')
	-- gnuplot.plotflush()
	-- gnuplot.close()
end

-- ()()
-- ('') HAANJU.YOO
