import argparse
import cv2
import sys
import numpy as np
import time
try:
    from tflite_runtime.interpreter import Interpreter
except:
    from tensorflow.lite.python.interpreter import Interpreter


def getKeypoints(probMap, threshold=0.1):

    mapSmooth = cv2.GaussianBlur(probMap, (3, 3), 0, 0)
    mapMask = np.uint8(mapSmooth>threshold)
    keypoints = []
    contours = None
    try:
        #OpenCV4.x
        contours, _ = cv2.findContours(mapMask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    except:
        #OpenCV3.x
        _, contours, _ = cv2.findContours(mapMask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours:
        blobMask = np.zeros(mapMask.shape)
        blobMask = cv2.fillConvexPoly(blobMask, cnt, 1)
        maskedProbMap = mapSmooth * blobMask
        _, maxVal, _, maxLoc = cv2.minMaxLoc(maskedProbMap)
        keypoints.append(maxLoc + (probMap[maxLoc[1], maxLoc[0]],))

    return keypoints


def getValidPairs(outputs, w, h):
    valid_pairs = []
    invalid_pairs = []
    n_interp_samples = 10
    paf_score_th = 0.1
    conf_th = 0.7

    for k in range(len(mapIdx)):
        pafA = outputs[0, mapIdx[k][0], :, :]
        pafB = outputs[0, mapIdx[k][1], :, :]
        pafA = cv2.resize(pafA, (w, h))
        pafB = cv2.resize(pafB, (w, h))

        candA = detected_keypoints[POSE_PAIRS[k][0]]
        candB = detected_keypoints[POSE_PAIRS[k][1]]
        nA = len(candA)
        nB = len(candB)

        if( nA != 0 and nB != 0):
            valid_pair = np.zeros((0,3))
            for i in range(nA):
                max_j=-1
                maxScore = -1
                found = 0
                for j in range(nB):
                    d_ij = np.subtract(candB[j][:2], candA[i][:2])
                    norm = np.linalg.norm(d_ij)
                    if norm:
                        d_ij = d_ij / norm
                    else:
                        continue
                    interp_coord = list(zip(np.linspace(candA[i][0], candB[j][0], num=n_interp_samples),
                                            np.linspace(candA[i][1], candB[j][1], num=n_interp_samples)))
                    paf_interp = []
                    for k in range(len(interp_coord)):
                        paf_interp.append([pafA[int(round(interp_coord[k][1])), int(round(interp_coord[k][0]))],
                                           pafB[int(round(interp_coord[k][1])), int(round(interp_coord[k][0]))] ])
                    paf_scores = np.dot(paf_interp, d_ij)
                    avg_paf_score = sum(paf_scores)/len(paf_scores)

                    if ( len(np.where(paf_scores > paf_score_th)[0]) / n_interp_samples ) > conf_th :
                        if avg_paf_score > maxScore:
                            max_j = j
                            maxScore = avg_paf_score
                            found = 1
                if found:
                    valid_pair = np.append(valid_pair, [[candA[i][3], candB[max_j][3], maxScore]], axis=0)

            valid_pairs.append(valid_pair)
        else:
            invalid_pairs.append(k)
            valid_pairs.append([])
    return valid_pairs, invalid_pairs


def getPersonwiseKeypoints(valid_pairs, invalid_pairs):
    personwiseKeypoints = -1 * np.ones((0, 19))

    for k in range(len(mapIdx)):
        if k not in invalid_pairs:
            partAs = valid_pairs[k][:,0]
            partBs = valid_pairs[k][:,1]
            indexA, indexB = np.array(POSE_PAIRS[k])

            for i in range(len(valid_pairs[k])):
                found = 0
                person_idx = -1
                for j in range(len(personwiseKeypoints)):
                    if personwiseKeypoints[j][indexA] == partAs[i]:
                        person_idx = j
                        found = 1
                        break

                if found:
                    personwiseKeypoints[person_idx][indexB] = partBs[i]
                    personwiseKeypoints[person_idx][-1] += keypoints_list[partBs[i].astype(int), 2] + valid_pairs[k][i][2]

                elif not found and k < 17:
                    row = -1 * np.ones(19)
                    row[indexA] = partAs[i]
                    row[indexB] = partBs[i]
                    row[-1] = sum(keypoints_list[valid_pairs[k][i,:2].astype(int), 2]) + valid_pairs[k][i][2]
                    personwiseKeypoints = np.vstack([personwiseKeypoints, row])
    return personwiseKeypoints

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="mobilenet_v2_pose_256_256_dm100_integer_quant.tflite", help="Path of the detection model.")
    parser.add_argument("--usbcamno", type=int, default=0, help="USB Camera number.")
    parser.add_argument("--camera_type", default="usb_cam", help="set usb_cam or raspi_cam or video_file")
    parser.add_argument("--camera_width", type=int, default=640, help="width.")
    parser.add_argument("--camera_height", type=int, default=480, help="height.")
    parser.add_argument("--vidfps", type=int, default=150, help="Frame rate.")
    parser.add_argument("--num_threads", type=int, default=4, help="Threads.")
    parser.add_argument("--input_video_file", default='', help="Input video file")
    args = parser.parse_args()

    model = args.model
    usbcamno = args.usbcamno
    camera_type = args.camera_type
    width = args.camera_width
    height = args.camera_height
    vidfps = args.vidfps
    num_threads = args.num_threads

    fps = ""
    framecount = 0
    time1 = 0
    elapsedTime = 0

    keypointsMapping = ['Nose', 'Neck', 'R-Sho', 'R-Elb', 'R-Wr', 'L-Sho', 'L-Elb', 'L-Wr', 'R-Hip', 'R-Knee',
                        'R-Ank', 'L-Hip', 'L-Knee', 'L-Ank', 'R-Eye', 'L-Eye', 'R-Ear', 'L-Ear']
    POSE_PAIRS = [[1,2], [1,5], [2,3], [3,4], [5,6], [6,7], [1,8], [8,9], [9,10], [1,11],
                [11,12], [12,13], [1,0], [0,14], [14,16], [0,15], [15,17], [2,17], [5,16]]
    mapIdx = [[31,32], [39,40], [33,34], [35,36], [41,42], [43,44], [19,20], [21,22], [23,24], [25,26],
            [27,28], [29,30], [47,48], [49,50], [53,54], [51,52], [55,56], [37,38], [45,46]]
    colors = [[0,100,255], [0,100,255], [0,255,255], [0,100,255], [0,255,255],
            [0,100,255], [0,255,0], [255,200,100], [255,0,255], [0,255,0],
            [255,200,100], [255,0,255], [0,0,255], [255,0,0], [200,200,0],
            [255,0,0], [200,200,0], [0,0,0]]

    if args.input_video_file != "":
        # WORKAROUND
        print("[Info] --input_video_file has an argument. so --device was replaced to 'video_file'.")
        camera_type = "video_file"

    if camera_type == "usb_cam":
        cam = cv2.VideoCapture(usbcamno)
        cam.set(cv2.CAP_PROP_FPS, vidfps)
        cam.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    elif camera_type == "raspi_cam":
        from picamera.array import PiRGBArray
        from picamera import PiCamera
        cam = PiCamera()
        cam.resolution = (width, height)
        stream = PiRGBArray(cam)
    elif camera_type == "video_file":
        cam = cv2.VideoCapture(args.input_video_file)

    else:
        print('[Error] --camera_type: wrong device')
        parser.print_help()
        sys.exit()

    cv2.namedWindow('pose estimation pi', cv2.WINDOW_AUTOSIZE)

    interpreter = Interpreter(model_path=model)
    interpreter.allocate_tensors()
    try:
        interpreter.set_num_threads(int(num_threads))
    except:
        print("WARNING: The installed PythonAPI of Tensorflow/Tensorflow Lite runtime does not support Multi-Thread processing.")
        print("WARNING: It works in single thread mode.")
        print("WARNING: If you want to use Multi-Thread to improve performance on aarch64/armv7l platforms, please refer to one of the below to implement a customized Tensorflow/Tensorflow Lite runtime.")
        print("https://github.com/PINTO0309/Tensorflow-bin.git")
        print("https://github.com/PINTO0309/TensorflowLite-bin.git")
        pass
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    input_shape = input_details[0]['shape']

    h = input_details[0]['shape'][1] #256
    w = input_details[0]['shape'][2] #256

    threshold = 0.25
    nPoints = 18

    try:

        while True:
            t1 = time.perf_counter()

            if camera_type == 'raspi_cam':
                cam.capture(stream, 'bgr', use_video_port=True)
                color_image = stream.array
                stream.truncate(0)
            else:
                ret, color_image = cam.read()
                # color_image = color_image[30:510, 160:800] # resize
                if not ret:
                    continue

            colw = color_image.shape[1]
            colh = color_image.shape[0]
            new_w = int(colw * min(w/colw, h/colh))
            new_h = int(colh * min(w/colw, h/colh))

            resized_image = cv2.resize(color_image, (new_w, new_h), interpolation = cv2.INTER_CUBIC)
            canvas = np.full((h, w, 3), 128)
            canvas[(h - new_h)//2:(h - new_h)//2 + new_h,(w - new_w)//2:(w - new_w)//2 + new_w, :] = resized_image

            prepimg = canvas.astype(np.float32)
            prepimg = prepimg[np.newaxis, :, :, :]     # Batch size axis add
            interpreter.set_tensor(input_details[0]['index'], prepimg)
            interpreter.invoke()
            outputs = interpreter.get_tensor(output_details[0]['index']) #(1, 32, 32, 57)
            outputs = outputs.transpose((0, 3, 1, 2))  # NHWC to NCHW, (1, 57, 32, 32)

            detected_keypoints = []
            keypoints_list = np.zeros((0, 3))
            keypoint_id = 0

            for part in range(nPoints):
                probMap = outputs[0, part, :, :]
                probMap = cv2.resize(probMap, (canvas.shape[1], canvas.shape[0])) # (256, 256)
                keypoints = getKeypoints(probMap, threshold)
                keypoints_with_id = []

                for i in range(len(keypoints)):
                    keypoints_with_id.append(keypoints[i] + (keypoint_id,))
                    keypoints_list = np.vstack([keypoints_list, keypoints[i]])
                    keypoint_id += 1

                detected_keypoints.append(keypoints_with_id)

            frameClone = np.uint8(canvas.copy())
            for i in range(nPoints):
                for j in range(len(detected_keypoints[i])):
                    cv2.circle(frameClone, detected_keypoints[i][j][0:2], 5, colors[i], -1, cv2.LINE_AA)

            valid_pairs, invalid_pairs = getValidPairs(outputs, w, h)
            personwiseKeypoints = getPersonwiseKeypoints(valid_pairs, invalid_pairs)

            for i in range(17):
                for n in range(len(personwiseKeypoints)):
                    index = personwiseKeypoints[n][np.array(POSE_PAIRS[i])]
                    if -1 in index:
                        continue
                    B = np.int32(keypoints_list[index.astype(int), 0])
                    A = np.int32(keypoints_list[index.astype(int), 1])
                    cv2.line(frameClone, (B[0], A[0]), (B[1], A[1]), colors[i], 3, cv2.LINE_AA)

            cv2.putText(frameClone, fps, (w-170,15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (38,0,255), 1, cv2.LINE_AA)
            frameClone = cv2.resize(frameClone, (colw, colw))
            cv2.imshow("pose estimation pi" , frameClone)

            key = cv2.waitKey(1)
            if key == 27 or key == ord('q'): # when ESC key or q key is pressed break
                break

            # FPS calculation
            framecount += 1
            if framecount >= 15:
                fps = "(Playback) {:.1f} FPS".format(time1/15)
                framecount = 0
                time1 = 0
            t2 = time.perf_counter()
            elapsedTime = t2-t1
            time1 += 1/elapsedTime

    except:
        import traceback
        traceback.print_exc()

    finally:

        print("\n\nFinished\n\n")
